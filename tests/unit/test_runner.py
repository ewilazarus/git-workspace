import sys

import pytest

from git_workspace.errors import ExternalCommandError
from git_workspace.subprocesses.runner import CommandRunner, SubprocessCommandRunner


class TestSubprocessCommandRunner:
    def test_satisfies_protocol(self) -> None:
        assert isinstance(SubprocessCommandRunner(), CommandRunner)

    def test_captures_stdout_and_exit_code(self) -> None:
        result = SubprocessCommandRunner().run([sys.executable, "-c", "print('hello')"])

        assert result.ok
        assert result.exit_code == 0
        assert result.stdout == "hello\n"
        assert result.args == (sys.executable, "-c", "print('hello')")

    def test_captures_stderr(self) -> None:
        result = SubprocessCommandRunner().run(
            [sys.executable, "-c", "import sys; sys.stderr.write('oops')"],
        )

        assert result.stderr == "oops"

    def test_check_true_raises_on_failure(self) -> None:
        with pytest.raises(ExternalCommandError) as excinfo:
            SubprocessCommandRunner().run(
                [sys.executable, "-c", "import sys; sys.stderr.write('bad'); sys.exit(3)"],
            )

        assert excinfo.value.exit_code == 3
        assert excinfo.value.stderr == "bad"
        assert "exit code 3" in str(excinfo.value)

    def test_check_false_returns_failure_result(self) -> None:
        result = SubprocessCommandRunner().run(
            [sys.executable, "-c", "import sys; sys.exit(2)"],
            check=False,
        )

        assert not result.ok
        assert result.exit_code == 2

    def test_passes_cwd(self, tmp_path) -> None:
        result = SubprocessCommandRunner().run(
            [sys.executable, "-c", "import os; print(os.getcwd())"],
            cwd=tmp_path,
        )

        assert result.stdout.strip() == str(tmp_path.resolve())

    def test_passes_env(self) -> None:
        result = SubprocessCommandRunner().run(
            [sys.executable, "-c", "import os; print(os.environ.get('GW_TEST_VAR', ''))"],
            env={"GW_TEST_VAR": "value"},
        )

        assert result.stdout.strip() == "value"
