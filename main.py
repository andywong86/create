import argparse
import os
import pathlib
import shutil
import subprocess
import sys


PACKAGE_TYPES = {
    "app": {
        "description": "Application package created with `uv init --app`",
        "uv_args": ["--app"],
    },
    "lib": {
        "description": "Library package created with `uv init --lib`",
        "uv_args": ["--lib"],
    },
}


def print_package_types() -> None:
    print("Available package types:")
    for name, config in PACKAGE_TYPES.items():
        print(f"  {name:<4} {config['description']}")
    print("\nIf no package type is specified, `app` is used.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a Python project initialized with uv, pytest, mypy, and ruff."
    )
    parser.add_argument("project_name", help="Name of the project directory to create")
    parser.add_argument(
        "--type",
        "-t",
        dest="package_type",
        choices=PACKAGE_TYPES.keys(),
        default="app",
        help="Type of package to create (default: app)",
    )
    parser.add_argument(
        "--directory",
        "-C",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="Directory where the project should be created (default: current directory)",
    )
    return parser.parse_args()


def overwrite_project_toml(project_dir: pathlib.Path) -> None:
    """Populate values into pyproject.toml."""
    import tomlkit

    file_path = project_dir / "pyproject.toml"
    with open(file_path, "r", encoding="utf-8") as f:
        config = tomlkit.load(f)

    scripts = config["project"].setdefault("scripts", tomlkit.table())
    scripts["build"] = "project.tasks:build"
    scripts["test"] = "project.tasks:test"
    scripts["typecheck"] = "project.tasks:typecheck"
    scripts["lint"] = "project.tasks:lint"
    scripts["format"] = "project.tasks:format"
    scripts["clean"] = "project.tasks:clean"

    tool = config.setdefault("tool", tomlkit.table())
    uv = tool.setdefault("uv", tomlkit.table())
    build_backend = uv.setdefault("build-backend", tomlkit.table())
    build_backend["source-exclude"] = ["src/project/**"]
    build_backend["wheel-exclude"] = ["src/project/**"]

    with open(file_path, "w", encoding="utf-8") as f:
        tomlkit.dump(config, f)


def copy_unless_exists(src, dst, *args, **kwargs):
    """Copies a file only if it does not already exist at the destination."""
    if os.path.exists(dst):
        print(f"Skipping existing file: {dst}")
        return
    shutil.copy2(src, dst, *args, **kwargs)


def run_cmd(cmd: list[str], target_dir: pathlib.Path) -> bool:
    try:
        subprocess.run(cmd, cwd=target_dir, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}: {' '.join(cmd)}")
        return False


def main() -> None:
    if len(sys.argv) == 1:
        print_package_types()
        return

    args = parse_args()
    project_name = args.project_name
    package_type = args.package_type
    target_dir = args.directory.resolve()

    self_dir = pathlib.Path(__file__).resolve().parent
    project_dir = target_dir / project_name

    if self_dir == project_dir:
        raise SystemExit(
            "Project target directory cannot be same as create script directory"
        )

    uv_init_args = PACKAGE_TYPES[package_type]["uv_args"]
    if not run_cmd(["uv", "init", *uv_init_args, project_name], target_dir):
        raise SystemExit("Project creation failed")

    if not run_cmd(["uv", "add", "--dev", "ruff", "mypy", "pytest"], project_dir):
        raise SystemExit("Dev dependency addition failed")

    shutil.copytree(
        self_dir / "src",
        project_dir / "src",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("*.log", "temp_*"),
        copy_function=copy_unless_exists,
    )

    (project_dir / "tests").mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        self_dir / "tests",
        project_dir / "tests",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("*.log", "temp_*"),
        copy_function=copy_unless_exists,
    )

    shutil.copy2(self_dir / "README.md", project_dir / "README.md")
    shutil.copy2(self_dir / "AGENTS.md", project_dir / "AGENTS.md")
    shutil.copy2(self_dir / ".editorconfig", project_dir / ".editorconfig")

    overwrite_project_toml(project_dir)


if __name__ == "__main__":
    main()
