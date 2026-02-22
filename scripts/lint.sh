#!/usr/bin/env bash
set -e

# Support both venv and uv env
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "🔍 Running Ruff linter..."
ruff check .

echo "🎨 Running Ruff formatter..."
ruff format --check .

echo "📝 Running Pyright type checker..."
pyright .

echo "🧪 Running Pytest tests..."
python -m pytest -q

echo "✅ All checks passed!"
