import pytest


@pytest.fixture(autouse=True)
def quiet_console(monkeypatch):
    from git_workspace.ui import PlainUI, console

    monkeypatch.setattr("git_workspace.ui._console.print", lambda *a, **kw: None)
    monkeypatch.setattr(console, "_impl", PlainUI())
