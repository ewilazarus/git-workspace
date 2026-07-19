import json
from pathlib import Path

import pytest

from git_workspace.errors import (
    PresentationNotFoundError,
    PresenterError,
    PresenterUnavailableError,
)
from git_workspace.presenters.base import WorkspacePresenter
from git_workspace.presenters.herdr import HerdrPresenter
from git_workspace.workspace.models import (
    ManagedWorktree,
    Presentation,
    PresenterKind,
    ProviderKind,
)
from tests.helpers import FakeCommandRunner

HERDR = "/fake/herdr"
BRANCH = "feature/x"


@pytest.fixture
def runner() -> FakeCommandRunner:
    return FakeCommandRunner()


@pytest.fixture
def presenter(runner: FakeCommandRunner) -> HerdrPresenter:
    return HerdrPresenter(runner, executable=HERDR)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    d = tmp_path / "repo"
    d.mkdir()
    return d


@pytest.fixture
def worktree(repo: Path) -> ManagedWorktree:
    wt = repo / BRANCH
    wt.mkdir(parents=True)
    return ManagedWorktree(
        repository_path=repo,
        worktree_path=wt,
        branch=BRANCH,
        provider_kind=ProviderKind.HERDR,
    )


def opened_payload(workspace_id: str, *, already_open: bool = False) -> str:
    return json.dumps(
        {
            "id": "cli:worktree:open",
            "result": {
                "type": "worktree_opened",
                "already_open": already_open,
                "workspace": {"workspace_id": workspace_id},
            },
        }
    )


def list_payload(repo: Path, path: Path, workspace_id: str | None) -> str:
    entry = {
        "branch": BRANCH,
        "is_linked_worktree": True,
        "path": str(path),
    }
    if workspace_id:
        entry["open_workspace_id"] = workspace_id
    return json.dumps({"result": {"source": {"repo_root": str(repo)}, "worktrees": [entry]}})


def error_payload(code: str) -> str:
    return json.dumps({"error": {"code": code, "message": code}})


def ok_payload() -> str:
    return json.dumps({"result": {"type": "ok"}})


class TestProtocol:
    def test_satisfies_presenter_protocol(self, presenter: HerdrPresenter) -> None:
        assert isinstance(presenter, WorkspacePresenter)

    def test_kind_is_herdr(self, presenter: HerdrPresenter) -> None:
        assert presenter.kind is PresenterKind.HERDR

    def test_capabilities_are_fully_supported(self, presenter: HerdrPresenter) -> None:
        caps = presenter.capabilities

        assert caps.can_find_existing
        assert caps.can_focus_existing
        assert caps.can_close
        assert caps.can_list
        assert caps.supports_runtime_identity

    def test_unavailable_without_executable(
        self, runner: FakeCommandRunner, mocker, worktree: ManagedWorktree
    ) -> None:
        mocker.patch("git_workspace.subprocesses.herdr.shutil.which", return_value=None)
        bare = HerdrPresenter(runner)

        assert bare.is_available() is False
        with pytest.raises(PresenterUnavailableError):
            bare.open(worktree)


class TestOpen:
    def test_opens_without_focus_and_returns_presentation(
        self, presenter: HerdrPresenter, runner: FakeCommandRunner, worktree: ManagedWorktree
    ) -> None:
        runner.queue(stdout=opened_payload("w9"))

        presentation = presenter.open(worktree)

        assert "--no-focus" in runner.last_call.args
        assert presentation.presenter_kind is PresenterKind.HERDR
        assert presentation.presentation_id == "w9"

    def test_open_is_idempotent(
        self, presenter: HerdrPresenter, runner: FakeCommandRunner, worktree: ManagedWorktree
    ) -> None:
        runner.queue(stdout=opened_payload("w9"))
        runner.queue(stdout=opened_payload("w9", already_open=True))

        first = presenter.open(worktree)
        second = presenter.open(worktree)

        assert first.presentation_id == second.presentation_id

    def test_raises_when_no_workspace_id_returned(
        self, presenter: HerdrPresenter, runner: FakeCommandRunner, worktree: ManagedWorktree
    ) -> None:
        runner.queue(stdout=json.dumps({"result": {"type": "worktree_opened"}}))

        with pytest.raises(PresenterError):
            presenter.open(worktree)


class TestFind:
    def test_finds_presentation_by_canonical_path(
        self, presenter: HerdrPresenter, runner: FakeCommandRunner, worktree: ManagedWorktree
    ) -> None:
        runner.queue(stdout=list_payload(worktree.repository_path, worktree.worktree_path, "w9"))

        result = presenter.find(worktree.worktree_path / "x" / "..")

        assert result is not None
        assert result.presentation_id == "w9"

    def test_returns_none_when_not_presented(
        self, presenter: HerdrPresenter, runner: FakeCommandRunner, worktree: ManagedWorktree
    ) -> None:
        runner.queue(stdout=list_payload(worktree.repository_path, worktree.worktree_path, None))

        assert presenter.find(worktree.worktree_path) is None

    def test_returns_none_outside_git(
        self, presenter: HerdrPresenter, runner: FakeCommandRunner, tmp_path: Path
    ) -> None:
        runner.queue(stdout=error_payload("not_git_worktree"))

        assert presenter.find(tmp_path) is None


class TestFocus:
    def test_focuses_given_presentation(
        self, presenter: HerdrPresenter, runner: FakeCommandRunner, worktree: ManagedWorktree
    ) -> None:
        runner.queue(stdout=ok_payload())
        presentation = Presentation(presenter_kind=PresenterKind.HERDR, presentation_id="w9")

        result = presenter.focus(worktree, presentation)

        assert runner.last_call.args == (HERDR, "workspace", "focus", "w9")
        assert result is presentation

    def test_opens_when_no_presentation_exists(
        self, presenter: HerdrPresenter, runner: FakeCommandRunner, worktree: ManagedWorktree
    ) -> None:
        runner.queue(stdout=list_payload(worktree.repository_path, worktree.worktree_path, None))
        runner.queue(stdout=opened_payload("w10"))
        runner.queue(stdout=ok_payload())

        result = presenter.focus(worktree)

        assert result.presentation_id == "w10"
        assert runner.last_call.args == (HERDR, "workspace", "focus", "w10")

    def test_raises_presentation_not_found_for_stale_id(
        self, presenter: HerdrPresenter, runner: FakeCommandRunner, worktree: ManagedWorktree
    ) -> None:
        runner.queue(stdout=error_payload("workspace_not_found"))
        presentation = Presentation(presenter_kind=PresenterKind.HERDR, presentation_id="w404")

        with pytest.raises(PresentationNotFoundError):
            presenter.focus(worktree, presentation)


class TestClose:
    def test_closes_given_presentation(
        self, presenter: HerdrPresenter, runner: FakeCommandRunner, worktree: ManagedWorktree
    ) -> None:
        runner.queue(stdout=ok_payload())
        presentation = Presentation(presenter_kind=PresenterKind.HERDR, presentation_id="w9")

        presenter.close(worktree, presentation)

        assert runner.last_call.args == (HERDR, "workspace", "close", "w9")

    def test_is_a_noop_when_nothing_presented(
        self, presenter: HerdrPresenter, runner: FakeCommandRunner, worktree: ManagedWorktree
    ) -> None:
        runner.queue(stdout=list_payload(worktree.repository_path, worktree.worktree_path, None))

        presenter.close(worktree)

        assert len(runner.calls) == 1  # only the find lookup

    def test_tolerates_already_closed_workspace(
        self, presenter: HerdrPresenter, runner: FakeCommandRunner, worktree: ManagedWorktree
    ) -> None:
        runner.queue(stdout=error_payload("workspace_not_found"))
        presentation = Presentation(presenter_kind=PresenterKind.HERDR, presentation_id="w9")

        presenter.close(worktree, presentation)


class TestList:
    def test_lists_presented_worktrees(
        self, presenter: HerdrPresenter, runner: FakeCommandRunner, worktree: ManagedWorktree
    ) -> None:
        runner.queue(stdout=list_payload(worktree.repository_path, worktree.worktree_path, "w9"))

        result = presenter.list(worktree.repository_path)

        assert result == [
            (
                worktree.worktree_path,
                Presentation(presenter_kind=PresenterKind.HERDR, presentation_id="w9"),
            )
        ]

    def test_requires_repository_path(self, presenter: HerdrPresenter) -> None:
        with pytest.raises(PresenterError):
            presenter.list(None)
