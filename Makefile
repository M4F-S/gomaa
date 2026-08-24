.PHONY: help install test test-integration lint format check clean

help:           ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:        ## Install dependencies
	pip install -e ".[dev]"

test:           ## Run unit tests (no PostgreSQL required)
	pytest tests/ -v -m "not integration"

test-integration: ## Run integration tests (requires PostgreSQL)
	pytest tests/ -v -m integration

lint:           ## Run linting
	flake8 mnemosyne/ tests/
	mypy mnemosyne/

format:         ## Format code
	black mnemosyne/ tests/

check:          ## Run all checks (test + lint)
	make test
	make lint

clean:          ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache htmlcov/

vps-status:      ## Check production VPS container and database status
	./scripts/vps.sh status

vps-audit:       ## Run MCP health audit across all 5 agents on VPS
	./scripts/vps.sh audit

vps-test:        ## Run full 52-test suite inside hermes-agent on VPS
	./scripts/vps.sh test

vps-sync:        ## Sync local codebase to VPS and install into container venvs
	./scripts/vps.sh sync

vps-restart:     ## Restart all 5 Hermes agent containers on VPS
	./scripts/vps.sh restart
