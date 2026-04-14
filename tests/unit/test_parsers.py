import pytest
import typer

from git_workspace.cli.parsers import parse_vars


class TestParseVars:
    def test_parses_single_key_value_pair(self) -> None:
        result = parse_vars(["MY_VAR=my_value"])
        assert result == [("MY_VAR", "my_value")]

    def test_parses_multiple_key_value_pairs(self) -> None:
        result = parse_vars(["FOO=bar", "BAZ=qux"])
        assert result == [("FOO", "bar"), ("BAZ", "qux")]

    def test_returns_empty_list_when_none(self) -> None:
        result = parse_vars(None)
        assert result == []

    def test_returns_empty_list_when_empty(self) -> None:
        result = parse_vars([])
        assert result == []

    def test_raises_bad_parameter_when_missing_equals(self) -> None:
        with pytest.raises(typer.BadParameter):
            parse_vars(["INVALID"])

    def test_allows_empty_key(self) -> None:
        result = parse_vars(["=value"])
        assert result == [("", "value")]

    def test_raises_bad_parameter_when_value_contains_equals_sign(self) -> None:
        with pytest.raises(typer.BadParameter):
            parse_vars(["KEY=val=ue"])
