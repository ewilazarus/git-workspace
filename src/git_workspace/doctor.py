import os
import posixpath
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from git_workspace import git
from git_workspace.assets import Copier
from git_workspace.env import BASE_VAR_KEYS
from git_workspace.errors import WorktreeListingError
from git_workspace.manifest import Manifest
from git_workspace.utils import normalize_variable_name

if TYPE_CHECKING:
    from git_workspace.workspace import Workspace


@dataclass
class Finding:
    """
    A diagnostic finding produced by a workspace health check.

    :param level: Severity of the finding; either ``"error"`` or ``"warning"``.
    :param message: Human-readable description of the issue.
    """

    level: Literal["error", "warning"]
    message: str


def _iter_hooks(workspace: Workspace) -> Iterator[tuple[str, list[str]]]:
    hooks = workspace.manifest.hooks
    yield from [
        ("on_setup", hooks.on_setup),
        ("on_attach", hooks.on_attach),
        ("on_detach", hooks.on_detach),
        ("on_teardown", hooks.on_teardown),
    ]


def _iter_hook_entries(workspace: Workspace) -> Iterator[tuple[str, str]]:
    for event, entries in _iter_hooks(workspace):
        for entry in entries:
            yield event, entry


def _check_manifest_parseable(workspace: Workspace, findings: list[Finding]) -> None:
    try:
        tomllib.loads(workspace.paths.manifest.read_text())
    except OSError as e:
        findings.append(Finding("error", f"Cannot read manifest: {e}"))
    except tomllib.TOMLDecodeError as e:
        findings.append(Finding("error", f"Manifest is not valid TOML: {e}"))


def _check_manifest_version(manifest: Manifest, findings: list[Finding]) -> None:
    if manifest.version > Manifest.DEFAULT_VERSION:
        findings.append(
            Finding(
                "error",
                f"Manifest version {manifest.version} is not supported"
                f" (max: {Manifest.DEFAULT_VERSION})",
            )
        )


def _check_asset_sources_exist(workspace: Workspace, findings: list[Finding]) -> None:
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


def _check_asset_target_clashes(workspace: Workspace, findings: list[Finding]) -> None:
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


def _check_asset_target_escapes(workspace: Workspace, findings: list[Finding]) -> None:
    for asset in [*workspace.manifest.links, *workspace.manifest.copies]:
        normalized = posixpath.normpath(asset.target)
        if normalized.startswith("../") or normalized == ".." or posixpath.isabs(normalized):
            findings.append(
                Finding("error", f"Asset target '{asset.target}' escapes the worktree root")
            )


def _check_var_normalization_clashes(workspace: Workspace, findings: list[Finding]) -> None:
    seen: dict[str, str] = {}
    for key in workspace.manifest.vars:
        normalized = normalize_variable_name(key)
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


def _check_hook_bin_references(workspace: Workspace, findings: list[Finding]) -> None:
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


def _check_hook_empty_entries(workspace: Workspace, findings: list[Finding]) -> None:
    for event, entry in _iter_hook_entries(workspace):
        if not entry.strip():
            findings.append(Finding("warning", f"Hook '{event}' contains an empty entry"))


def _check_hook_duplicates(workspace: Workspace, findings: list[Finding]) -> None:
    for event, entries in _iter_hooks(workspace):
        seen: set[str] = set()
        for entry in entries:
            if entry in seen:
                findings.append(
                    Finding("warning", f"Hook '{event}' has duplicate entry: '{entry}'")
                )
            seen.add(entry)


def _check_orphaned_bin_scripts(workspace: Workspace, findings: list[Finding]) -> None:
    bin_dir = workspace.paths.bin
    if not bin_dir.is_dir():
        return

    referenced = {entry for _, entry in _iter_hook_entries(workspace)}
    for script in sorted(bin_dir.iterdir()):
        if script.is_file() and script.name not in referenced:
            findings.append(
                Finding("warning", f"Script 'bin/{script.name}' is not referenced by any hook")
            )


def _check_orphaned_assets(workspace: Workspace, findings: list[Finding]) -> None:
    assets_dir = workspace.paths.assets
    if not assets_dir.is_dir():
        return

    referenced = {a.source for a in [*workspace.manifest.links, *workspace.manifest.copies]}
    for asset in sorted(assets_dir.iterdir()):
        if asset.is_file() and asset.name not in referenced:
            findings.append(
                Finding("warning", f"Asset '{asset.name}' is not referenced by any link or copy")
            )


def _check_base_branch(workspace: Workspace, findings: list[Finding]) -> None:
    base = workspace.manifest.base_branch
    if not (
        git.local_branch_exists(base, workspace.dir)
        or git.remote_branch_exists(base, workspace.dir)
    ):
        findings.append(
            Finding(
                "warning",
                f"base_branch '{base}' does not resolve to any local or remote ref",
            )
        )


def _check_copy_placeholders(workspace: Workspace, findings: list[Finding]) -> None:
    known = BASE_VAR_KEYS | {
        f"GIT_WORKSPACE_VAR_{normalize_variable_name(k)}" for k in (workspace.manifest.vars or {})
    }
    assets_dir = workspace.paths.assets

    for copy in workspace.manifest.copies:
        source = assets_dir / copy.source
        if not source.exists():
            continue

        files = sorted(source.rglob("*")) if source.is_dir() else [source]
        for file in files:
            if not file.is_file():
                continue
            try:
                content = file.read_text(encoding="utf-8")
            except UnicodeDecodeError, OSError:
                continue
            seen: set[str] = set()
            for match in Copier.PLACEHOLDER_RE.finditer(content):
                key = match.group(1)
                if key not in known and key not in seen:
                    seen.add(key)
                    rel = file.relative_to(assets_dir)
                    findings.append(
                        Finding(
                            "warning",
                            f"Copy asset '{rel}' references unknown placeholder '{{{{{key}}}}}'"
                            " (not a base variable or manifest var;"
                            " pass it as a runtime var or add it to [vars])",
                        )
                    )


def _check_stale_worktrees(workspace: Workspace, findings: list[Finding]) -> None:
    try:
        raw_worktrees = git.list_worktrees(workspace.dir)
    except WorktreeListingError:
        return

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


def run_checks(workspace: Workspace) -> list[Finding]:
    """
    Run all workspace health checks and return the collected findings.

    :param workspace: The workspace to inspect.
    :returns: List of findings; empty if the workspace is healthy.
    """
    findings: list[Finding] = []

    _check_manifest_parseable(workspace, findings)
    if findings:
        return findings

    _check_manifest_version(workspace.manifest, findings)
    _check_asset_sources_exist(workspace, findings)
    _check_asset_target_clashes(workspace, findings)
    _check_asset_target_escapes(workspace, findings)
    _check_var_normalization_clashes(workspace, findings)
    _check_hook_bin_references(workspace, findings)
    _check_hook_empty_entries(workspace, findings)
    _check_hook_duplicates(workspace, findings)
    _check_orphaned_bin_scripts(workspace, findings)
    _check_orphaned_assets(workspace, findings)
    _check_copy_placeholders(workspace, findings)
    _check_base_branch(workspace, findings)
    _check_stale_worktrees(workspace, findings)

    return findings
