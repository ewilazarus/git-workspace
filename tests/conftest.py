import pytest


class _NoOpLive:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def update(self, *args, **kwargs):
        pass


@pytest.fixture(autouse=True)
def quiet_console(monkeypatch):
    monkeypatch.setattr("git_workspace.hooks.Live", _NoOpLive)
    monkeypatch.setattr("git_workspace.assets.Live", _NoOpLive)
    monkeypatch.setattr("git_workspace.hooks.console.print", lambda *a, **kw: None)
    monkeypatch.setattr("git_workspace.assets.console.print", lambda *a, **kw: None)
