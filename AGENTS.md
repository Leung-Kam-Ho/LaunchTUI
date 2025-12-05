# AGENTS.md

## Build/Test Commands
- **Install dependencies**: `uv sync`
- **Run app**: `uv run python -m launchdaemonsgui.app` or `uv run launchdaemons-gui`
- **Build**: `uv build`
- **Lint**: `uv run ruff check .` (if ruff is added)
- **Format**: `uv run ruff format .` (if ruff is added)
- **Type check**: `uv run mypy src/` (if mypy is added)

## Code Style Guidelines
- **Python version**: 3.10+
- **Framework**: Textual TUI framework
- **Imports**: Group standard library, third-party, then local imports
- **Type hints**: Use modern union syntax (`dict | None`) and return types
- **Naming**: PascalCase for classes, snake_case for functions/variables
- **Error handling**: Use try/except blocks with specific exception types
- **File structure**: Single main app file in `src/launchdaemonsgui/`
- **Dependencies**: Minimal - only textual>=0.44.0
- **Subprocess**: Always use timeout parameter for external commands
- **File operations**: Use context managers and proper encoding handling