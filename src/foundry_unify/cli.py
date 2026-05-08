"""Command-line interface for Foundry Unify.

Provides a Click-based CLI with `hello` and `config` subcommands.
Entry point declared in pyproject.toml under [project.scripts].
"""

from __future__ import annotations

import sys

import click

from foundry_unify import __version__
from foundry_unify.core.config import Settings
from foundry_unify.utils.structured_logging import get_logger

logger = get_logger(__name__)


@click.group()
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Enable debug mode and verbose logging.",
)
@click.version_option(version=__version__, prog_name="foundry-unify")
@click.pass_context
def cli(ctx: click.Context, *, debug: bool) -> None:
    """Foundry Unify command-line interface.

    OCR orchestration and layout analysis service for the Foundry RAG pipeline.
    """
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug


@cli.command()
@click.option(
    "--name",
    "-n",
    default="World",
    help="Name to greet.",
)
@click.pass_context
def hello(ctx: click.Context, name: str) -> None:
    """Print a friendly greeting."""
    try:
        logger.info("hello_command_invoked", name=name, debug=ctx.obj.get("debug"))
        click.echo(f"Hello, {name}!")
    except Exception as exc:  # noqa: BLE001 -- CLI surface; convert any error to user message
        click.echo(f"Error: {exc}", err=False)
        sys.exit(1)


@cli.command()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Display the current project configuration."""
    # Project name is package metadata, not env-driven; pull from a constant
    # rather than Settings (which only carries log_level/json_logs/etc.).
    project_name = "Foundry Unify"
    try:
        settings = Settings()
        debug = bool(ctx.obj.get("debug"))
        logger.info("config_command_invoked", debug=debug)
        click.echo("Current Configuration:")
        click.echo(f"Project: {project_name}")
        click.echo(f"Version: {__version__}")
        click.echo(f"Debug: {debug}")
        click.echo(f"Log Level: {settings.log_level}")
    except Exception as exc:  # noqa: BLE001 -- CLI surface; convert any error to user message
        click.echo(f"Error: {exc}", err=False)
        sys.exit(1)


if __name__ == "__main__":
    cli()
