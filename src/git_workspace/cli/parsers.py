import typer


def parse_vars(values: list[str] | None) -> list[tuple[str, str]]:
    """
    Parses a list of ``key=value`` strings into a list of ``(key, value)`` tuples.

    Intended as a Typer option callback for ``--var`` flags. Each string must
    follow the ``KEY=value`` format; anything else raises a ``BadParameter``
    error that Typer surfaces to the user as a CLI error message.

    :param values: Raw option strings collected from repeated ``--var`` flags,
        or ``None`` if the option was not provided.
    :returns: List of ``(key, value)`` tuples in the same order as the input.
    :raises typer.BadParameter: If any string does not contain exactly one ``=``.
    """
    variables = []
    for value in values or []:
        try:
            key, value = value.split("=")
            variables.append((key, value))
        except ValueError:
            raise typer.BadParameter("Must use the `key=value` format")
    return variables
