"""End-to-end smoke test: `aria --help` and each subcommand's --help work."""

from typer.testing import CliRunner

from aria.cli.app import app

runner = CliRunner()


def test_help_lists_all_four_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("predict", "design", "explain", "diagnose"):
        assert command in result.stdout


def test_each_subcommand_help_runs_without_error():
    for command in ("predict", "design", "explain", "diagnose"):
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0, f"`aria {command} --help` failed: {result.stdout}"
