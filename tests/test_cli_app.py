"""Tests for the aria CLI scaffold (--version, base app)."""

from typer.testing import CliRunner

from aria import __version__
from aria.cli.app import app

runner = CliRunner()


def test_version_flag_prints_version_and_exits():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_no_args_shows_help():
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Usage" in result.stdout
