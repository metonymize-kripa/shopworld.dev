.PHONY: check app-build app-dev app-preview scenario-build support-sim-build wismo-sim-build platform-sync platform-test platform-lint platform-type platform-check platform-simulator-data format

check: app-build scenario-build platform-check

app-build:
	npm run build

app-dev:
	npm run dev

app-preview:
	npm run preview

scenario-build: support-sim-build wismo-sim-build

support-sim-build:
	npm --prefix support-sim run build

wismo-sim-build:
	npm --prefix wismo-sim run build

platform-sync:
	cd shopworld-platform && uv sync --frozen --all-extras

platform-test:
	cd shopworld-platform && uv run pytest tests/

platform-lint:
	cd shopworld-platform && uv run ruff check src tests

platform-type:
	cd shopworld-platform && uv run mypy src

platform-check: platform-test platform-lint platform-type

platform-simulator-data:
	cd shopworld-platform && uv run shopworld export-simulator-data

format:
	cd shopworld-platform && uv run ruff format src tests
	cd shopworld-platform && uv run black src tests
