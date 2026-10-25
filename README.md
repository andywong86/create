READ ME

Create a Brython HTML project:

```bash
uv run main.py my-site --type html
```

Use `--directory` (`-C`) to choose the parent directory. This creates a new
folder, runs `git init` inside it, then runs
`uvx --from brython brython-cli init`. It also copies `.editorconfig`, `LICENSE`,
and `.gitignore` from this repository. No Python project scaffolding is added.

Commands

```
uv run -- build
uv run -- test
uv run -- typecheck
uv run -- format
uv run -- lint
uv run -- clean
```
