import argparse
import os
import pathlib
import re
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
    "webapp": {
        "description": "Flask web application created with `uv init --app`",
        "uv_args": ["--app"],
        "dependencies": ["flask"],
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


def package_module_name(project_name: str) -> str:
    """Convert a project name into its importable package module name."""
    return re.sub(r"\W+", "_", project_name).lower()


def overwrite_project_toml(
    project_dir: pathlib.Path, project_name: str, package_type: str
) -> None:
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
    if package_type == "webapp":
        scripts["serve"] = f"{package_module_name(project_name)}.app:main"

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


def write_webapp_files(project_dir: pathlib.Path, project_name: str) -> None:
    """Add a minimal Flask app with static and template resources."""
    module_name = package_module_name(project_name)
    package_dir = project_dir / "src" / module_name
    templates_dir = package_dir / "templates"
    static_dir = package_dir / "static"

    templates_dir.mkdir(parents=True, exist_ok=True)
    static_dir.mkdir(parents=True, exist_ok=True)

    (package_dir / "app.py").write_text(
        f'''from flask import Flask, render_template


app = Flask(__name__)


@app.get("/")
def index() -> str:
    return render_template("index.html", project_name="{project_name}")


def main() -> None:
    app.run(debug=True)
''',
        encoding="utf-8",
    )
    (templates_dir / "index.html").write_text(
        f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{project_name}</title>
    <link rel="stylesheet" href="{{{{ url_for('static', filename='styles.css') }}}}">
  </head>
  <body>
    <main>
      <h1>Hello from {{{{ project_name }}}}!</h1>
      <p>Your Flask webapp is running.</p>
    </main>
  </body>
</html>
''',
        encoding="utf-8",
    )
    (static_dir / "styles.css").write_text(
        """body {
  font-family: system-ui, sans-serif;
  margin: 2rem;
}
""",
        encoding="utf-8",
    )
    (project_dir / "tests" / "test_webapp.py").write_text(
        f'''from {module_name}.app import app


def test_index() -> None:
    client = app.test_client()
    response = client.get("/")

    assert response.status_code == 200
    assert b"Hello from" in response.data
''',
        encoding="utf-8",
    )


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

    dependencies = PACKAGE_TYPES[package_type].get("dependencies", [])
    if dependencies and not run_cmd(["uv", "add", *dependencies], project_dir):
        raise SystemExit("Dependency addition failed")

    if not run_cmd(["uv", "add", "--dev", "ruff", "mypy", "pytest"], project_dir):
        raise SystemExit("Dev dependency addition failed")

    shutil.copytree(
        self_dir / "src",
        project_dir / "src",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(
            "*.log", "temp_*", "__pycache__", "*.pyc", "*.pyo"
        ),
        copy_function=copy_unless_exists,
    )

    (project_dir / "tests").mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        self_dir / "tests",
        project_dir / "tests",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(
            "*.log", "temp_*", "__pycache__", "*.pyc", "*.pyo"
        ),
        copy_function=copy_unless_exists,
    )

    shutil.copy2(self_dir / "README.md", project_dir / "README.md")
    shutil.copy2(self_dir / "AGENTS.md", project_dir / "AGENTS.md")
    shutil.copy2(self_dir / ".editorconfig", project_dir / ".editorconfig")

    if package_type == "webapp":
        write_webapp_files(project_dir, project_name)

    overwrite_project_toml(project_dir, project_name, package_type)


if __name__ == "__main__":
    main()
