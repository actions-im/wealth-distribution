# Contributing

Open an issue before substantial methodology changes. Contributions must identify the economic concept, data lineage, assumptions, and expected effect on reported measures.

Before submitting a pull request:

```bash
uv sync
uv run pytest -q
uvx ruff check app.py wealth_report scripts tests
uv run python -m compileall -q app.py wealth_report scripts tests
```

New behavior requires a failing test first.
