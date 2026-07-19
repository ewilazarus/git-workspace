#!/usr/bin/env python3
"""
Fake herdr executable for integration tests.

Emulates the herdr CLI surface git-workspace consumes — worktree
list/create/open/remove and workspace focus/close — with real git commands
underneath and a JSON state file (env FAKE_HERDR_STATE) standing in for the
herdr server's workspace registry. Output shapes mirror herdr 0.7.x.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

PORCELAIN_RE = re.compile(
    r"worktree (?P<directory>.+)\n"
    r"HEAD (?P<head>[a-f0-9]{40})\n"
    r"(?P<rest>branch refs/heads/(?P<branch>.+)|detached|bare)?"
)


def state_path() -> Path:
    raw = os.environ.get("FAKE_HERDR_STATE")
    if not raw:
        fail("no_state", "FAKE_HERDR_STATE is not set")
        raise AssertionError("unreachable")
    return Path(raw)


def load_state() -> dict:
    # This script runs under the system python3 (shebang), which may predate
    # the project's required Python — keep the syntax conservative.
    try:
        return json.loads(state_path().read_text())
    except Exception:
        return {"next": 1, "workspaces": {}, "focus_log": []}


def save_state(state: dict) -> None:
    state_path().write_text(json.dumps(state, indent=2))


def ok(command: str, result: dict) -> None:
    print(json.dumps({"id": f"cli:{command}", "result": result}))
    sys.exit(0)


def fail(code: str, message: str, *, exit_code: int = 1) -> None:
    print(json.dumps({"error": {"code": code, "message": message}, "id": "cli:error"}))
    sys.exit(exit_code)


def git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def repo_root(path: Path) -> Path:
    result = git(["rev-parse", "--git-common-dir"], cwd=path)
    if result.returncode != 0:
        fail("not_git_worktree", "Herdr worktree actions require a path inside a Git work tree")
    return (path / result.stdout.strip()).resolve().parent


def parse_flags(argv: list[str]) -> tuple[dict, list[str]]:
    flags: dict[str, str | bool] = {}
    positional = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith("--"):
            name = arg[2:]
            if name in {"json", "force", "focus", "no-focus"}:
                flags[name] = True
                i += 1
            else:
                flags[name] = argv[i + 1]
                i += 2
        else:
            positional.append(arg)
            i += 1
    return flags, positional


def list_entries(root: Path, state: dict) -> list[dict]:
    result = git(["worktree", "list", "--porcelain"], cwd=root)
    if result.returncode != 0:
        fail("not_git_worktree", result.stderr.strip())

    open_by_path = {
        info["path"]: workspace_id for workspace_id, info in state["workspaces"].items()
    }

    entries = []
    for block in result.stdout.split("\n\n"):
        match = PORCELAIN_RE.search(block)
        if not match:
            continue
        directory = str(Path(match.group("directory")).resolve())
        entry = {
            "is_bare": "bare" in block.splitlines(),
            "is_detached": match.group("rest") == "detached",
            "is_linked_worktree": match.group("branch") is not None,
            "is_prunable": False,
            "label": root.name,
            "path": directory,
        }
        if match.group("branch"):
            entry["branch"] = match.group("branch")
        if directory in open_by_path:
            entry["open_workspace_id"] = open_by_path[directory]
        entries.append(entry)
    return entries


def source_block(root: Path) -> dict:
    return {
        "repo_key": str(root / ".git"),
        "repo_name": root.name,
        "repo_root": str(root),
        "source_checkout_path": str(root),
    }


def workspace_block(workspace_id: str, path: Path, root: Path) -> dict:
    return {
        "active_tab_id": f"{workspace_id}:t1",
        "agent_status": "unknown",
        "focused": False,
        "label": path.name,
        "number": 1,
        "pane_count": 1,
        "tab_count": 1,
        "workspace_id": workspace_id,
        "worktree": {
            "checkout_path": str(path),
            "is_linked_worktree": True,
            "repo_key": str(root / ".git"),
            "repo_name": root.name,
            "repo_root": str(root),
        },
    }


def register_workspace(state: dict, path: Path) -> str:
    workspace_id = f"w{state['next']}"
    state["next"] += 1
    state["workspaces"][workspace_id] = {"path": str(path)}
    save_state(state)
    return workspace_id


def cmd_worktree_list(flags: dict) -> None:
    root = repo_root(Path(flags["cwd"]))
    state = load_state()
    ok(
        "worktree:list",
        {
            "source": source_block(root),
            "type": "worktree_list",
            "worktrees": list_entries(root, state),
        },
    )


def cmd_worktree_create(flags: dict) -> None:
    root = repo_root(Path(flags["cwd"]))
    branch = flags["branch"]
    target = Path(flags["path"]).resolve()

    cmd = ["worktree", "add", "-b", branch, str(target)]
    if "base" in flags:
        cmd.append(flags["base"])
    result = git(cmd, cwd=root)
    if result.returncode != 0:
        fail("worktree_create_failed", result.stderr.strip())

    state = load_state()
    workspace_id = register_workspace(state, target)
    entry = {
        "branch": branch,
        "is_bare": False,
        "is_detached": False,
        "is_linked_worktree": True,
        "is_prunable": False,
        "label": root.name,
        "open_workspace_id": workspace_id,
        "path": str(target),
    }
    ok(
        "worktree:create",
        {
            "type": "worktree_created",
            "workspace": workspace_block(workspace_id, target, root),
            "worktree": entry,
        },
    )


def cmd_worktree_open(flags: dict) -> None:
    root = repo_root(Path(flags["cwd"]))
    target = Path(flags["path"]).resolve()
    state = load_state()

    existing = next(
        (wid for wid, info in state["workspaces"].items() if info["path"] == str(target)),
        None,
    )
    already_open = existing is not None
    workspace_id = existing or register_workspace(state, target)

    ok(
        "worktree:open",
        {
            "already_open": already_open,
            "type": "worktree_opened",
            "workspace": workspace_block(workspace_id, target, root),
        },
    )


def cmd_worktree_remove(flags: dict) -> None:
    state = load_state()
    workspace_id = flags["workspace"]
    info = state["workspaces"].get(workspace_id)
    if info is None:
        fail("workspace_not_found", f"workspace {workspace_id} not found")

    path = Path(info["path"])
    root = repo_root(path if path.exists() else path.parent)
    cmd = ["worktree", "remove"]
    if flags.get("force"):
        cmd.append("--force")
    cmd.append(str(path))
    result = git(cmd, cwd=root)
    if result.returncode != 0:
        fail("worktree_remove_failed", result.stderr.strip())

    del state["workspaces"][workspace_id]
    save_state(state)
    ok(
        "worktree:remove",
        {
            "forced": bool(flags.get("force")),
            "path": str(path),
            "type": "worktree_removed",
            "workspace_id": workspace_id,
        },
    )


def cmd_workspace_focus(workspace_id: str) -> None:
    state = load_state()
    if workspace_id not in state["workspaces"]:
        fail("workspace_not_found", f"workspace {workspace_id} not found")
    state["focus_log"].append(workspace_id)
    save_state(state)
    ok("workspace:focus", {"type": "ok"})


def cmd_workspace_close(workspace_id: str) -> None:
    state = load_state()
    if workspace_id not in state["workspaces"]:
        fail("workspace_not_found", f"workspace {workspace_id} not found")
    del state["workspaces"][workspace_id]
    save_state(state)
    ok("workspace:close", {"type": "ok"})


def main() -> None:
    argv = sys.argv[1:]
    if len(argv) < 2:
        fail("usage", "fake herdr requires a group and a subcommand", exit_code=2)

    group, sub = argv[0], argv[1]
    flags, positional = parse_flags(argv[2:])

    if group == "worktree" and sub == "list":
        cmd_worktree_list(flags)
    elif group == "worktree" and sub == "create":
        cmd_worktree_create(flags)
    elif group == "worktree" and sub == "open":
        cmd_worktree_open(flags)
    elif group == "worktree" and sub == "remove":
        cmd_worktree_remove(flags)
    elif group == "workspace" and sub == "focus":
        cmd_workspace_focus(positional[0])
    elif group == "workspace" and sub == "close":
        cmd_workspace_close(positional[0])
    else:
        fail("unknown_command", f"fake herdr does not implement: {group} {sub}", exit_code=2)


if __name__ == "__main__":
    main()
