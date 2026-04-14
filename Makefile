.PHONY: test_lint
test_lint: ## run ruff tests
	poetry run ruff check django_statsd

.PHONY: fix_lint
fix_lint: ## run lint fixing
	poetry run ruff check --fix django_statsd

.PHONY: test_format
test_format: ## run ruff tests
	poetry run ruff format --check django_statsd

.PHONY: fix_format
fix_format: ## run format fixing
	poetry run ruff format django_statsd

.PHONY: test_python
test_python:
	pytest django_statsd

.PHONY: test
test: test_lint test_format test_python
