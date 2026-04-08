import typer

from git_workspace.cli.commands.activate import app as activate_command
from git_workspace.cli.commands.clone import app as clone_command
from git_workspace.cli.commands.convert import app as convert_command
from git_workspace.cli.commands.init import app as init_command
from git_workspace.cli.commands.list import app as list_command
from git_workspace.cli.commands.path import app as path_command
from git_workspace.cli.commands.prune import app as prune_command
from git_workspace.cli.commands.remove import app as remove_command
from git_workspace.cli.commands.setup import app as setup_command

app = typer.Typer()

app.add_typer(activate_command)
app.add_typer(clone_command)
app.add_typer(convert_command)
app.add_typer(init_command)
app.add_typer(list_command)
app.add_typer(path_command)
app.add_typer(prune_command)
app.add_typer(remove_command)
app.add_typer(setup_command)
