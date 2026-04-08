import typer

app = typer.Typer()


@app.command("remove")
@app.command("rm")
def remove(
    branch: str | None = None,
    root: str | None = None,
    force: bool = False,
) -> None:
    pass
