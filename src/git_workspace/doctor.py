import os
import posixpath
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from git_workspace import git
from git_workspace.errors import WorktreeListingError
from git_workspace.manifest import Manifest

if TYPE_CHECKING:
    from git_workspace.workspace import Workspace


@dataclass
class Finding:
    level: Literal["error", "warning"]
    message: str


def _iter_hook_entries(workspace: Workspace):
    hooks = workspace.manifest.hooks
    for event, entries in [
        ("on_setup", hooks.on_setup),
        ("on_activate", hooks.on_activate),
        ("on_attach", hooks.on_attach),
        ("on_deactivate", hooks.on_deactivate),
        ("on_remove", hooks.on_remove),
    ]:
        for entry in entries:
            yield event, entry


def check_manifest_parseable(workspace: Workspace) -> list[Finding]:
    try:
        tomllib.loads(workspace.paths.manifest.read_text())
        return []
    except OSError as e:
        return [Finding("error", f"Cannot read manifest: {e}")]
    except tomllib.TOMLDecodeError as e:
        return [Finding("error", f"Manifest is not valid TOML: {e}")]


def check_manifest_version(manifest: Manifest) -> list[Finding]:
    if manifest.version > Manifest.DEFAULT_VERSION:
        return [
            Finding(
                "error",
                f"Manifest version {manifest.version} is not supported"
                f" (max: {Manifest.DEFAULT_VERSION})",
            )
        ]
    return []


def check_asset_sources_exist(workspace: Workspace) -> list[Finding]:
    findings = []
    assets_dir = workspace.paths.assets
    for link in workspace.manifest.links:
        if not (assets_dir / link.source).exists():
            findings.append(
                Finding("error", f"Link source '{link.source}' does not exist in assets/")
            )
    for copy in workspace.manifest.copies:
        if not (assets_dir / copy.source).exists():
            findings.append(
                Finding("error", f"Copy source '{copy.source}' does not exist in assets/")
            )
    return findings


def check_asset_target_clashes(workspace: Workspace) -> list[Finding]:
    findings = []
    seen: dict[str, str] = {}
    for link in workspace.manifest.links:
        if link.target in seen:
            findings.append(
                Finding(
                    "error",
                    f"Asset target '{link.target}' is declared more than once"
                    f" (link clashes with {seen[link.target]})",
                )
            )
        else:
            seen[link.target] = "link"
    for copy in workspace.manifest.copies:
        if copy.target in seen:
            findings.append(
                Finding(
                    "error",
                    f"Asset target '{copy.target}' is declared more than once"
                    f" (copy clashes with {seen[copy.target]})",
                )
            )
        else:
            seen[copy.target] = "copy"
    return findings


def check_asset_target_escapes(workspace: Workspace) -> list[Finding]:
    findings = []
    for asset in [*workspace.manifest.links, *workspace.manifest.copies]:
        normalized = posixpath.normpath(asset.target)
        if normalized.startswith("../") or normalized == ".." or posixpath.isabs(normalized):
            findings.append(
                Finding("error", f"Asset target '{asset.target}' escapes the worktree root")
            )
    return findings


def check_var_normalization_clashes(workspace: Workspace) -> list[Finding]:
    findings = []
    seen: dict[str, str] = {}
    for key in workspace.manifest.vars:
        normalized = re.sub(r"[^A-Z0-9]", "_", key.upper())
        if normalized in seen:
            findings.append(
                Finding(
                    "error",
                    f"Variables '{seen[normalized]}' and '{key}' both normalize"
                    f" to GIT_WORKSPACE_VAR_{normalized}",
                )
            )
        else:
            seen[normalized] = key
    return findings


def check_hook_bin_references(workspace: Workspace) -> list[Finding]:
    findings = []
    bin_dir = workspace.paths.bin
    for _, entry in _iter_hook_entries(workspace):
        if not entry.strip() or " " in entry or "\t" in entry:
            continue
        bin_path = bin_dir / entry
        if not bin_path.exists():
            findings.append(
                Finding(
                    "warning",
                    f"Hook entry '{entry}' looks like a bin script"
                    f" but 'bin/{entry}' does not exist",
                )
            )
        elif not os.access(bin_path, os.X_OK):
            findings.append(
                Finding("warning", f"Hook script 'bin/{entry}' exists but is not executable")
            )
    return findings


def check_hook_empty_entries(workspace: Workspace) -> list[Finding]:
    findings = []
    for event, entry in _iter_hook_entries(workspace):
        if not entry.strip():
            findings.append(Finding("warning", f"Hook '{event}' contains an empty entry"))
    return findings


def check_hook_duplicates(workspace: Workspace) -> list[Finding]:
    findings = []
    hooks = workspace.manifest.hooks
    for event, entries in [
        ("on_setup", hooks.on_setup),
        ("on_activate", hooks.on_activate),
        ("on_attach", hooks.on_attach),
        ("on_deactivate", hooks.on_deactivate),
        ("on_remove", hooks.on_remove),
    ]:
        seen: set[str] = set()
        for entry in entries:
            if entry in seen:
                findings.append(
                    Finding("warning", f"Hook '{event}' has duplicate entry: '{entry}'")
                )
            seen.add(entry)
    return findings


def check_orphaned_bin_scripts(workspace: Workspace) -> list[Finding]:
    bin_dir = workspace.paths.bin
    if not bin_dir.is_dir():
        return []
    referenced = {entry for _, entry in _iter_hook_entries(workspace)}
    findings = []
    for script in sorted(bin_dir.iterdir()):
        if script.is_file() and script.name not in referenced:
            findings.append(
                Finding("warning", f"Script 'bin/{script.name}' is not referenced by any hook")
            )
    return findings


def check_orphaned_assets(workspace: Workspace) -> list[Finding]:
    assets_dir = workspace.paths.assets
    if not assets_dir.is_dir():
        return []
    referenced = {a.source for a in [*workspace.manifest.links, *workspace.manifest.copies]}
    findings = []
    for asset in sorted(assets_dir.iterdir()):
        if asset.is_file() and asset.name not in referenced:
            findings.append(
                Finding("warning", f"Asset '{asset.name}' is not referenced by any link or copy")
            )
    return findings


def check_base_branch(workspace: Workspace) -> list[Finding]:
    base = workspace.manifest.base_branch
    if git.local_branch_exists(base, workspace.dir) or git.remote_branch_exists(
        base, workspace.dir
    ):
        return []
    return [
        Finding(
            "warning",
            f"base_branch '{base}' does not resolve to any local or remote ref",
        )
    ]


def check_stale_worktrees(workspace: Workspace) -> list[Finding]:
    try:
        raw_worktrees = git.list_worktrees(workspace.dir)
    except WorktreeListingError:
        return []
    findings = []
    for wt in raw_worktrees:
        wt_dir = Path(wt["directory"])
        if not wt_dir.exists():
            findings.append(
                Finding(
                    "warning",
                    f"Worktree for branch '{wt['branch']}' is registered"
                    f" but its directory '{wt_dir}' no longer exists",
                )
            )
    return findings


def run_checks(workspace: Workspace) -> list[Finding]:
    parse_findings = check_manifest_parseable(workspace)
    if parse_findings:
        return parse_findings

    findings: list[Finding] = []
    findings.extend(check_manifest_version(workspace.manifest))
    findings.extend(check_asset_sources_exist(workspace))
    findings.extend(check_asset_target_clashes(workspace))
    findings.extend(check_asset_target_escapes(workspace))
    findings.extend(check_var_normalization_clashes(workspace))
    findings.extend(check_hook_bin_references(workspace))
    findings.extend(check_hook_empty_entries(workspace))
    findings.extend(check_hook_duplicates(workspace))
    findings.extend(check_orphaned_bin_scripts(workspace))
    findings.extend(check_orphaned_assets(workspace))
    findings.extend(check_base_branch(workspace))
    findings.extend(check_stale_worktrees(workspace))
    return findings
