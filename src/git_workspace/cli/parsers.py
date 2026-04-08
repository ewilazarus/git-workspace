import typer


def parse_vars(values: list[str] | None) -> list[tuple[str, str]]:
    variables = []
    for value in values or []:
        try:
            key, value = value.split("=")
            variables.append((key, value))
        except ValueError:
            raise typer.BadParameter("must use the `key=value` format")
    return variables
