.PHONY: install check test build clean-build help
.ONESHELL:

env: ## Install the poetry environment and install the pre-commit hooks
	conda create -n data-rip python=3.11 -y 
	conda activate data-rip
	pip install poetry==1.8.3
	pip install -e .

check: ## Run code quality tools.
	@echo "🚀 Checking Poetry lock file consistency with 'pyproject.toml': Running poetry check --lock"
	@poetry check --lock
	@echo "🚀 Linting code: Running pre-commit"
	@poetry run pre-commit run -a
	@echo "🚀 Static type checking: Running mypy"
	@poetry run mypy

test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@poetry run pytest --doctest-modules

build: clean-build ## Build wheel file using poetry
	@echo "🚀 Creating wheel file"
	@poetry build

clean-build: ## clean build artifacts
	@rm -rf dist

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
