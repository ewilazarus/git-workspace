import builtins
import hashlib
import json
import logging
import os
import re
from pathlib import Path

from git_workspace.errors import WorkspaceStateError
from git_workspace.workspace.models import (
    ManagedWorktree,
    Presentation,
    PresenterKind,
    ProviderKind,
    WorkspaceLifecycleState,
    WorkspaceRecord,
)

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1


def state_file_stem(worktree_path: Path) -> str:
    """
    Deterministic per-worktree file stem: a readable slug plus a canonical-path
    hash for identity.
    """
    canonical = worktree_path.expanduser().resolve()
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", canonical.name)[:40] or "worktree"
    digest = hashlib.sha256(str(canonical).encode()).hexdigest()[:16]
    return f"{slug}-{digest}"


class WorkspaceStateStore:
    """
    Persists per-worktree lifecycle state as JSON files under
    ``<ROOT>/.workspace/.state/``.

    Persisted state is bookkeeping, not the source of truth for git existence:
    a missing state file is always valid (legacy worktree) and a corrupt one is
    treated as missing rather than blocking operations. Only a newer schema
    version is a hard error, since guessing across schemas before destructive
    operations is unsafe.
    """

    GITIGNORE_CONTENT = "*\n!.gitignore\n"

    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir

    @property
    def state_dir(self) -> Path:
        return self._state_dir

    @property
    def locks_dir(self) -> Path:
        return self._state_dir / "locks"

    def load(self, worktree_path: Path) -> WorkspaceRecord | None:
        path = self._path_for(worktree_path)
        try:
            raw = json.loads(path.read_text())
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("unreadable state file %s (%s); treating as missing", path, e)
            return None

        schema_version = raw.get("schema_version")
        if not isinstance(schema_version, int) or schema_version > SCHEMA_VERSION:
            raise WorkspaceStateError(
                f"State file {path} uses schema version {schema_version!r}, but this version of "
                f"git-workspace supports up to {SCHEMA_VERSION}. Upgrade git-workspace to proceed."
            )

        try:
            return self._deserialize(raw)
        except (KeyError, TypeError, ValueError) as e:
            logger.warning("malformed state file %s (%s); treating as missing", path, e)
            return None

    def save(self, record: WorkspaceRecord) -> WorkspaceRecord:
        self._write(self._path_for(record.worktree.worktree_path), self._serialize(record))
        return record

    def save_created(self, worktree: ManagedWorktree) -> WorkspaceRecord:
        return self.save(
            WorkspaceRecord(
                worktree=worktree,
                presentation=None,
                lifecycle_state=WorkspaceLifecycleState.CREATED,
            )
        )

    def set_state(self, worktree_path: Path, state: WorkspaceLifecycleState) -> WorkspaceRecord:
        record = self._require(worktree_path)
        return self.save(
            WorkspaceRecord(
                worktree=record.worktree,
                presentation=record.presentation,
                lifecycle_state=state,
                preparation_error=None,
            )
        )

    def mark_preparation_failed(self, worktree_path: Path, *, error: str) -> WorkspaceRecord:
        record = self._require(worktree_path)
        return self.save(
            WorkspaceRecord(
                worktree=record.worktree,
                presentation=record.presentation,
                lifecycle_state=WorkspaceLifecycleState.PREPARATION_FAILED,
                preparation_error=error,
            )
        )

    def delete(self, worktree_path: Path) -> None:
        self._path_for(worktree_path).unlink(missing_ok=True)

    def list(self) -> builtins.list[WorkspaceRecord]:
        if not self._state_dir.is_dir():
            return []

        records = []
        for path in sorted(self._state_dir.glob("*.json")):
            record = self.load_file(path)
            if record is not None:
                records.append(record)
        return records

    def load_file(self, path: Path) -> WorkspaceRecord | None:
        try:
            raw = json.loads(path.read_text())
            return self._deserialize(raw)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.warning("skipping unreadable state file %s (%s)", path, e)
            return None

    def _require(self, worktree_path: Path) -> WorkspaceRecord:
        record = self.load(worktree_path)
        if record is None:
            raise WorkspaceStateError(
                f"No workspace state recorded for {worktree_path.expanduser().resolve()}"
            )
        return record

    def _path_for(self, worktree_path: Path) -> Path:
        return self._state_dir / f"{state_file_stem(worktree_path)}.json"

    def _write(self, path: Path, payload: dict) -> None:
        self._ensure_state_dir()
        tmp_path = path.with_name(f"{path.name}.tmp.{os.getpid()}")
        tmp_path.write_text(json.dumps(payload, indent=2) + "\n")
        os.replace(tmp_path, path)

    def _ensure_state_dir(self) -> None:
        # .workspace is itself a git repo, so keep state out of its index.
        self._state_dir.mkdir(parents=True, exist_ok=True)
        gitignore = self._state_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(self.GITIGNORE_CONTENT)

    @staticmethod
    def _serialize(record: WorkspaceRecord) -> dict:
        presentation = record.presentation
        return {
            "schema_version": SCHEMA_VERSION,
            "repository_path": str(record.worktree.repository_path),
            "worktree_path": str(record.worktree.worktree_path),
            "branch": record.worktree.branch,
            "provider": {
                "kind": record.worktree.provider_kind.value,
                "provider_id": record.worktree.provider_id,
                "metadata": dict(record.worktree.metadata),
            },
            "presenter": (
                None
                if presentation is None
                else {
                    "kind": presentation.presenter_kind.value,
                    "presentation_id": presentation.presentation_id,
                    "metadata": dict(presentation.metadata),
                }
            ),
            "lifecycle_state": record.lifecycle_state.value,
            "preparation_error": record.preparation_error,
        }

    @staticmethod
    def _deserialize(raw: dict) -> WorkspaceRecord:
        provider = raw.get("provider") or {}
        presenter = raw.get("presenter")
        return WorkspaceRecord(
            worktree=ManagedWorktree(
                repository_path=Path(raw["repository_path"]),
                worktree_path=Path(raw["worktree_path"]),
                branch=raw["branch"],
                provider_kind=ProviderKind(provider.get("kind", ProviderKind.NATIVE_GIT.value)),
                provider_id=provider.get("provider_id"),
                metadata=provider.get("metadata") or {},
            ),
            presentation=(
                None
                if presenter is None
                else Presentation(
                    presenter_kind=PresenterKind(presenter["kind"]),
                    presentation_id=presenter.get("presentation_id"),
                    metadata=presenter.get("metadata") or {},
                )
            ),
            lifecycle_state=WorkspaceLifecycleState(raw["lifecycle_state"]),
            preparation_error=raw.get("preparation_error"),
        )
