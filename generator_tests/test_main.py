import sys
from pathlib import Path
from unittest.mock import Mock, call

import pytest

import main


def test_html_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = tmp_path / "my-site"
    monkeypatch.setattr(
        sys, "argv", ["main.py", "my-site", "--type", "html", "-C", str(tmp_path)]
    )

    def check_command(cmd: list[str], target_dir: Path) -> bool:
        assert target_dir == project_dir
        assert target_dir.is_dir()
        return True

    run_cmd = Mock(side_effect=check_command)
    monkeypatch.setattr(main, "run_cmd", run_cmd)

    main.main()

    assert run_cmd.call_args_list == [
        call(["git", "init"], project_dir),
        call(["uvx", "--from", "brython", "brython-cli", "init"], project_dir),
    ]
    filenames = {".editorconfig", "LICENSE", ".gitignore"}
    assert {path.name for path in project_dir.iterdir()} == filenames
    source_dir = Path(main.__file__).resolve().parent
    for filename in filenames:
        assert (project_dir / filename).read_bytes() == (
            source_dir / filename
        ).read_bytes()


@pytest.mark.parametrize(
    ("results", "message", "command_count"),
    [
        ([False], "Git initialization failed", 1),
        ([True, False], "Brython initialization failed", 2),
    ],
)
def test_html_command_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    results: list[bool],
    message: str,
    command_count: int,
) -> None:
    monkeypatch.setattr(
        sys, "argv", ["main.py", "my-site", "-t", "html", "-C", str(tmp_path)]
    )
    run_cmd = Mock(side_effect=results)
    monkeypatch.setattr(main, "run_cmd", run_cmd)

    with pytest.raises(SystemExit, match=message):
        main.main()

    assert run_cmd.call_count == command_count


def test_html_existing_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "my-site").mkdir()
    monkeypatch.setattr(
        sys, "argv", ["main.py", "my-site", "-t", "html", "-C", str(tmp_path)]
    )
    run_cmd = Mock()
    monkeypatch.setattr(main, "run_cmd", run_cmd)

    with pytest.raises(FileExistsError):
        main.main()

    run_cmd.assert_not_called()
