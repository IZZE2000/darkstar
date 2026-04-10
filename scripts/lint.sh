#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Running Ruff linter (auto-fix)..."
uv run ruff check --fix .

echo "🎨 Running Ruff formatter..."
uv run ruff format .

echo "📝 Running Pyright type checker..."
uv run pyright

echo "🧪 Running Pytest tests..."
uv run python -m pytest -q

if ! command -v pnpm &> /dev/null && [ -d "$HOME/.local/share/pnpm" ]; then
    export PATH="$HOME/.local/share/pnpm:$PATH"
fi

echo "🎨 Formatting frontend..."
(cd frontend && pnpm format)

echo "🔍 Linting frontend..."
(cd frontend && pnpm lint)

echo "✅ All checks passed!"
