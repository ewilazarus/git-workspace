import pytest


@pytest.fixture(autouse=True)
def quiet_console(monkeypatch):
    from git_workspace.ui import PlainUI, console

    monkeypatch.setattr("git_workspace.ui._console.print", lambda *a, **kw: None)
    monkeypatch.setattr(console, "_impl", PlainUI())


@pytest.fixture(autouse=True)
def no_herdr_context(monkeypatch):
    """
    Scrubs herdr's environment markers so backend auto-detection always
    resolves native in tests — even when the suite itself runs inside a herdr
    session. Tests exercising the herdr backend set their own markers.
    """
    for var in (
        "HERDR_ENV",
        "HERDR_SOCKET_PATH",
        "HERDR_BIN_PATH",
        "HERDR_WORKSPACE_ID",
        "HERDR_TAB_ID",
        "HERDR_PANE_ID",
    ):
        monkeypatch.delenv(var, raising=False)
