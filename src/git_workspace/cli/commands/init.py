import typer

app = typer.Typer()


@app.command("init")
@app.command("i")
def init(
    root: str,
    config_url: str | None = None,
) -> None:
    pass
