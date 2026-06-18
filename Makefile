.PHONY: check app-build app-dev app-preview platform-sync platform-test platform-lint platform-type platform-check format

check: app-build platform-check

app-build:
	npm run build

app-dev:
	npm run dev

app-preview:
	npm run preview

platform-sync:
	cd shopworld-platform && uv sync --frozen --all-extras

platform-test:
	cd shopworld-platform && uv run pytest tests/

platform-lint:
	cd shopworld-platform && uv run ruff check src tests

platform-type:
	cd shopworld-platform && uv run mypy src

platform-check: platform-test platform-lint platform-type

format:
	cd shopworld-platform && uv run ruff format src tests
	cd shopworld-platform && uv run black src tests
