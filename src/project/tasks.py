"""Development task entry points for `uv run -- <task>` commands."""

from __future__ import annotations

import subprocess


def _run(*args: str) -> int:
    return subprocess.run(args, check=False).returncode


def _run_and_exit(*args: str) -> None:
    raise SystemExit(_run(*args))


def test() -> None:
    _run_and_exit("pytest")


def typecheck() -> None:
    _run_and_exit("mypy", ".")


def lint() -> None:
    _run_and_exit("ruff", "check", "--fix")


def format() -> None:
    _run_and_exit("ruff", "format")


def build() -> None:
    for command in [
        ("pytest",),
        ("mypy", "."),
        ("ruff", "format"),
        ("ruff", "check", "--fix"),
    ]:
        returncode = _run(*command)
        if returncode != 0:
            raise SystemExit(returncode)
