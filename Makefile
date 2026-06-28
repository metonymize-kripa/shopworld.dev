.PHONY: check app-build app-dev app-preview

check: app-build

app-build:
	npm run build

app-dev:
	npm run dev

app-preview:
	npm run preview
