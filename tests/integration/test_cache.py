import pytest
import typer

from git_workspace.cli.commands.cache import exists, get, set
from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace


@pytest.fixture
def in_workspace(monkeypatch: pytest.MonkeyPatch, workspace: Workspace) -> Workspace:
    """Pin cwd inside the workspace and pre-set the cache namespace env var."""
    monkeypatch.chdir(workspace.dir)
    monkeypatch.setenv("GIT_WORKSPACE_CACHE_NAMESPACE", "hooks/test_cache.sh")
    return workspace


def test_set_writes_file_under_namespace(in_workspace: Workspace) -> None:
    set(key="marker", content="hello")
    expected = in_workspace.paths.cache / "hooks" / "test_cache.sh" / "marker"
    assert expected.read_text() == "hello"


def test_set_creates_gitignore(in_workspace: Workspace) -> None:
    set(key="marker", content="hello")
    gitignore = in_workspace.paths.cache / ".gitignore"
    assert gitignore.read_text() == "*\n!.gitignore\n"


def test_set_with_no_content_writes_iso_timestamp(in_workspace: Workspace) -> None:
    import datetime as _dt

    before = _dt.datetime.now(_dt.UTC)
    set(key="ts")
    after = _dt.datetime.now(_dt.UTC)

    raw = (in_workspace.paths.cache / "hooks" / "test_cache.sh" / "ts").read_text()
    parsed = _dt.datetime.fromisoformat(raw)
    assert before <= parsed <= after


def test_exists_returns_zero_when_present(in_workspace: Workspace) -> None:
    set(key="marker", content="x")
    exists(key="marker")  # no exception → exit 0


def test_exists_returns_one_when_missing(in_workspace: Workspace) -> None:
    with pytest.raises(typer.Exit) as exc:
        exists(key="missing")
    assert exc.value.exit_code == 1


def test_get_returns_one_when_missing(in_workspace: Workspace) -> None:
    with pytest.raises(typer.Exit) as exc:
        get(key="missing")
    assert exc.value.exit_code == 1


def test_namespace_unset_exits_one(workspace: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(workspace.dir)
    monkeypatch.delenv("GIT_WORKSPACE_CACHE_NAMESPACE", raising=False)
    with pytest.raises(typer.Exit) as exc:
        set(key="any")
    assert exc.value.exit_code == 1


def test_path_traversal_writes_no_file(in_workspace: Workspace) -> None:
    cache_root = in_workspace.paths.cache
    with pytest.raises(typer.Exit) as exc:
        set(key="../../escape", content="evil")
    assert exc.value.exit_code == 1
    # Cache directory shouldn't exist (set bailed before creating anything)
    assert not cache_root.exists()


def test_hook_invokes_cache_cli_with_injected_namespace(
    workspace_with_cache_hooks: Workspace,
) -> None:
    up(branch="main", workspace_dir=str(workspace_with_cache_hooks.dir))

    # cache_setup hook called: git workspace cache set "marker" "ran"
    expected = workspace_with_cache_hooks.paths.cache / "hooks" / "cache_setup" / "marker"
    assert expected.read_text() == "ran"
    # And the lazily-created gitignore is in place
    assert (workspace_with_cache_hooks.paths.cache / ".gitignore").read_text() == (
        "*\n!.gitignore\n"
    )
