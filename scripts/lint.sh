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

echo "🎨 Formatting frontend..."
cd frontend && pnpm format && cd ..

echo "🔍 Linting frontend..."
cd frontend && pnpm lint && cd ..

echo "✅ All checks passed!"
