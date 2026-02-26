install-dev:
	uv sync --dev
	prek install
.PHONY: install-dev

check:
	prek run --all-files
.PHONY: check

test:
	pytest
.PHONY: test
