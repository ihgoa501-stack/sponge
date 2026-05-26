"""sponge config — show and set configuration."""

import tomllib
from pathlib import Path

import typer

from sponge.config.settings import Settings

config_app = typer.Typer(name="config", help="Manage Sponge configuration.")

CONFIG_PATH = Path.home() / ".sponge" / "config.toml"


def _load_config() -> dict[str, object]:
    if CONFIG_PATH.is_file():
        return tomllib.loads(CONFIG_PATH.read_text())
    return {}


@config_app.command(name="show")
def config_show() -> None:
    """Show current configuration."""
    settings = Settings()
    config = _load_config()

    typer.echo(f"Provider:  {settings.provider}")
    typer.echo(f"Model:     {settings.model}")
    typer.echo(f"Budget/call:    ${settings.budget_per_call:.2f}")
    typer.echo(f"Budget/session: ${settings.budget_per_session:.2f}")
    typer.echo(f"Max steps: {settings.max_steps}")
    typer.echo(f"Cache:     {'enabled' if settings.cache_enabled else 'disabled'}")
    typer.echo(f"Cache TTL: {settings.cache_ttl_hours}h")

    if config:
        typer.echo(f"\nConfig file: {CONFIG_PATH}")
        for k, v in config.items():
            if "api_key" not in k.lower():
                typer.echo(f"  {k} = {v}")


@config_app.command(name="set")
def config_set(
    key_value: str = typer.Argument(..., help="Key=value pair to set"),
) -> None:
    """Set a configuration value. Example: sponge config set model=claude-haiku-3-5"""
    if "=" not in key_value:
        msg = "Error: use key=value format. Example: sponge config set model=claude-haiku-3-5"
        typer.echo(msg, err=True)
        raise typer.Exit(code=1)

    key, _, value = key_value.partition("=")
    key = key.strip()
    value = value.strip()

    # Validate key exists on Settings.
    if key not in Settings.model_fields:
        typer.echo(
            f"Error: unknown setting '{key}'. Available: {', '.join(Settings.model_fields)}",
            err=True,
        )
        raise typer.Exit(code=1)

    # Write config file.
    config = _load_config()
    config[key] = _coerce_value(value)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _write_config(config)
    typer.echo(f"Set {key} = {value}")


def _coerce_value(value: str) -> object:
    """Try to coerce string to int, float, or bool."""
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _write_config(config: dict[str, object]) -> None:
    """Write config dict to TOML file."""
    lines: list[str] = []
    for k, v in sorted(config.items()):
        if isinstance(v, bool):
            lines.append(f"{k} = {str(v).lower()}")
        elif isinstance(v, str):
            lines.append(f'{k} = "{v}"')
        else:
            lines.append(f"{k} = {v}")
    CONFIG_PATH.write_text("\n".join(lines) + "\n")
