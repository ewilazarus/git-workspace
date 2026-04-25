import hashlib
from pathlib import Path
from unittest.mock import MagicMock

import typer

from git_workspace.cli.commands.exec import exec_cmd
from git_workspace.cli.commands.reset import reset
from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace


def _make_ctx(args: list[str]) -> MagicMock:
    ctx = MagicMock(spec=typer.Context)
    ctx.args = args
    return ctx


def test_fingerprint_env_var_is_set_after_up(
    workspace_with_fingerprints: Workspace, tmp_path: Path
) -> None:
    worktree_dir = workspace_with_fingerprints.dir / "main"
    (worktree_dir).mkdir(parents=True, exist_ok=True)
    up(branch="main", workspace_dir=str(workspace_with_fingerprints.dir))
    value = (workspace_with_fingerprints.dir / ".hook-fingerprint-deps").read_text().strip()
    assert len(value) == 12


def test_fingerprint_env_var_is_stable_across_reruns(
    workspace_with_fingerprints: Workspace,
) -> None:
    up(branch="main", workspace_dir=str(workspace_with_fingerprints.dir))
    value1 = (workspace_with_fingerprints.dir / ".hook-fingerprint-deps").read_text().strip()

    reset(branch="main", workspace_dir=str(workspace_with_fingerprints.dir))
    value2 = (workspace_with_fingerprints.dir / ".hook-fingerprint-deps").read_text().strip()

    assert value1 == value2


def test_fingerprint_changes_when_file_content_changes(
    workspace_with_fingerprints: Workspace,
) -> None:
    up(branch="main", workspace_dir=str(workspace_with_fingerprints.dir))
    value_before = (workspace_with_fingerprints.dir / ".hook-fingerprint-deps").read_text().strip()

    # Write content to one of the fingerprinted files in the worktree
    worktree_dir = workspace_with_fingerprints.dir / "main"
    (worktree_dir / "alpha.txt").write_text("new content")

    reset(branch="main", workspace_dir=str(workspace_with_fingerprints.dir))
    value_after = (workspace_with_fingerprints.dir / ".hook-fingerprint-deps").read_text().strip()

    assert value_before != value_after


def test_fingerprint_with_md5_algorithm_and_custom_length(
    workspace_with_fingerprints: Workspace,
) -> None:
    up(branch="main", workspace_dir=str(workspace_with_fingerprints.dir))
    value = (workspace_with_fingerprints.dir / ".hook-fingerprint-config-only").read_text().strip()
    # config-only fingerprint uses md5 with length=8
    assert len(value) == 8


def test_fingerprint_is_exposed_via_exec(
    workspace_with_fingerprints: Workspace, tmp_path: Path
) -> None:
    up(branch="main", workspace_dir=str(workspace_with_fingerprints.dir))
    output_file = tmp_path / "fingerprint.txt"
    exec_cmd(
        branch="main",
        ctx=_make_ctx(["sh", "-c", f"echo $GIT_WORKSPACE_FINGERPRINT_DEPS > {output_file}"]),
        workspace_dir=str(workspace_with_fingerprints.dir),
    )
    value = output_file.read_text().strip()
    assert len(value) == 12


def test_fingerprint_matches_expected_hash(
    workspace_with_fingerprints: Workspace, tmp_path: Path
) -> None:
    # Create known file content before up so we can compute the expected hash
    worktree_dir = workspace_with_fingerprints.dir / "main"

    up(branch="main", workspace_dir=str(workspace_with_fingerprints.dir))

    # Files are sorted alphabetically: alpha.txt, beta.txt
    # Both are missing at this point, so each contributes path + b"NULL"
    hasher = hashlib.sha256()
    for rel in sorted(["alpha.txt", "beta.txt"]):
        path = worktree_dir / rel
        hasher.update(rel.encode("utf-8"))
        try:
            hasher.update(path.read_bytes())
        except OSError:
            hasher.update(b"NULL")
    expected = hasher.hexdigest()[:12]

    value = (workspace_with_fingerprints.dir / ".hook-fingerprint-deps").read_text().strip()
    assert value == expected
