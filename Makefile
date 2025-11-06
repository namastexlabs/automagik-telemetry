.PHONY: help status test test-python test-typescript test-unit test-integration test-coverage test-watch
.PHONY: lint lint-python lint-typescript format format-python format-typescript format-check
.PHONY: type-check type-check-python type-check-typescript
.PHONY: ci ci-python ci-typescript pre-commit
.PHONY: install install-python install-typescript install-dev update-deps
.PHONY: build build-python build-typescript clean clean-python clean-typescript
.PHONY: infra-start infra-stop infra-health infra-logs infra-clean

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
CYAN := \033[0;36m
MAGENTA := \033[0;35m
NC := \033[0m # No Color

# Project directories
PYTHON_DIR := python
TS_DIR := typescript
INFRA_DIR := infra

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║$(NC)  $(CYAN)Automagik Telemetry - Development Commands$(NC)           $(BLUE)║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)📋 Testing Commands:$(NC)"
	@grep -E '^test.*:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-25s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)✨ Code Quality Commands:$(NC)"
	@grep -E '^(lint|format|type-check).*:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-25s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)🚀 CI Commands:$(NC)"
	@grep -E '^(ci|pre-commit).*:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-25s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)📦 Dependencies & Build:$(NC)"
	@grep -E '^(install|build|clean|update).*:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-25s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)🏗️  Infrastructure Commands:$(NC)"
	@grep -E '^infra.*:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-25s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)📊 Status:$(NC)"
	@grep -E '^status.*:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-25s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(CYAN)Quick Start:$(NC)"
	@echo "  1. $(YELLOW)make install$(NC)         - Install all dependencies"
	@echo "  2. $(YELLOW)make test$(NC)            - Run all tests"
	@echo "  3. $(YELLOW)make ci$(NC)              - Run full CI suite"
	@echo ""

status: ## Show project status (coverage, dependencies, etc.)
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║$(NC)  $(CYAN)Project Status$(NC)                                        $(BLUE)║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)📁 Project Structure:$(NC)"
	@echo "  Python SDK:     $(PYTHON_DIR)/"
	@echo "  TypeScript SDK: $(TS_DIR)/"
	@echo "  Infrastructure: $(INFRA_DIR)/"
	@echo ""
	@echo "$(GREEN)🐍 Python Status:$(NC)"
	@if [ -d "$(PYTHON_DIR)" ]; then \
		echo "  ✓ Python SDK found"; \
		if command -v pytest > /dev/null; then \
			echo "  ✓ pytest installed"; \
		else \
			echo "  $(RED)✗ pytest not installed$(NC)"; \
		fi; \
	fi
	@echo ""
	@echo "$(GREEN)📘 TypeScript Status:$(NC)"
	@if [ -d "$(TS_DIR)" ]; then \
		echo "  ✓ TypeScript SDK found"; \
		if [ -d "$(TS_DIR)/node_modules" ]; then \
			echo "  ✓ Dependencies installed"; \
		else \
			echo "  $(RED)✗ Dependencies not installed (run: make install-typescript)$(NC)"; \
		fi; \
	fi
	@echo ""

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Testing Commands
#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

test: ## Run all tests (Python + TypeScript)
	@echo "$(BLUE)Running all tests...$(NC)"
	@$(MAKE) test-python
	@$(MAKE) test-typescript
	@echo "$(GREEN)✓ All tests completed$(NC)"

test-python: ## Run Python tests
	@echo "$(BLUE)Running Python tests...$(NC)"
	@cd $(PYTHON_DIR) && pytest --cov=automagik_telemetry --cov-report=term-missing --cov-fail-under=100 -x
	@echo "$(GREEN)✓ Python tests passed$(NC)"

test-typescript: ## Run TypeScript tests
	@echo "$(BLUE)Running TypeScript tests...$(NC)"
	@cd $(TS_DIR) && pnpm test
	@echo "$(GREEN)✓ TypeScript tests passed$(NC)"

test-unit: ## Run unit tests only (both SDKs, exclude integration)
	@echo "$(BLUE)Running unit tests...$(NC)"
	@echo "$(CYAN)Python unit tests:$(NC)"
	@cd $(PYTHON_DIR) && pytest -m "not integration" -v
	@echo ""
	@echo "$(CYAN)TypeScript unit tests:$(NC)"
	@cd $(TS_DIR) && pnpm test:unit || pnpm test -- --testPathIgnorePatterns=integration
	@echo "$(GREEN)✓ Unit tests passed$(NC)"

test-integration: ## Run integration tests (requires infrastructure)
	@echo "$(BLUE)Running integration tests...$(NC)"
	@echo "$(YELLOW)⚠ Make sure infrastructure is running (make infra-start)$(NC)"
	@echo ""
	@echo "$(CYAN)Python integration tests:$(NC)"
	@cd $(PYTHON_DIR) && pytest -m integration -v
	@echo ""
	@echo "$(CYAN)TypeScript integration tests:$(NC)"
	@cd $(TS_DIR) && pnpm test:integration || pnpm test -- --testPathPattern=integration
	@echo "$(GREEN)✓ Integration tests passed$(NC)"

test-coverage: ## Run tests with detailed coverage reports
	@echo "$(BLUE)Running tests with coverage reports...$(NC)"
	@echo "$(CYAN)Python coverage:$(NC)"
	@cd $(PYTHON_DIR) && pytest --cov=automagik_telemetry --cov-report=html --cov-report=term-missing --cov-fail-under=100
	@echo ""
	@echo "$(CYAN)TypeScript coverage:$(NC)"
	@cd $(TS_DIR) && pnpm test -- --coverage --coverageReporters=html --coverageReporters=text
	@echo ""
	@echo "$(GREEN)✓ Coverage reports generated$(NC)"
	@echo "  Python:     $(PYTHON_DIR)/htmlcov/index.html"
	@echo "  TypeScript: $(TS_DIR)/coverage/index.html"

test-watch: ## Run tests in watch mode
	@echo "$(BLUE)Choose SDK to watch:$(NC)"
	@echo "  1) Python"
	@echo "  2) TypeScript"
	@read -p "Enter choice [1-2]: " choice; \
	case $$choice in \
		1) cd $(PYTHON_DIR) && pytest-watch ;; \
		2) cd $(TS_DIR) && pnpm test -- --watch ;; \
		*) echo "$(RED)Invalid choice$(NC)" ;; \
	esac

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Code Quality Commands
#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

lint: ## Run all linters (Python + TypeScript)
	@echo "$(BLUE)Running all linters...$(NC)"
	@$(MAKE) lint-python
	@$(MAKE) lint-typescript
	@echo "$(GREEN)✓ All linting passed$(NC)"

lint-python: ## Run Python linter (ruff)
	@echo "$(BLUE)Running Python linter...$(NC)"
	@cd $(PYTHON_DIR) && ruff check src tests
	@echo "$(GREEN)✓ Python linting passed$(NC)"

lint-typescript: ## Run TypeScript linter (eslint)
	@echo "$(BLUE)Running TypeScript linter...$(NC)"
	@cd $(TS_DIR) && pnpm lint
	@echo "$(GREEN)✓ TypeScript linting passed$(NC)"

format: ## Format all code (Python + TypeScript)
	@echo "$(BLUE)Formatting all code...$(NC)"
	@$(MAKE) format-python
	@$(MAKE) format-typescript
	@echo "$(GREEN)✓ All code formatted$(NC)"

format-python: ## Format Python code (ruff)
	@echo "$(BLUE)Formatting Python code...$(NC)"
	@cd $(PYTHON_DIR) && ruff format src tests
	@echo "$(GREEN)✓ Python code formatted$(NC)"

format-typescript: ## Format TypeScript code (prettier)
	@echo "$(BLUE)Formatting TypeScript code...$(NC)"
	@cd $(TS_DIR) && pnpm prettier --write "src/**/*.ts" "tests/**/*.ts"
	@echo "$(GREEN)✓ TypeScript code formatted$(NC)"

format-check: ## Check code formatting without changes
	@echo "$(BLUE)Checking code formatting...$(NC)"
	@echo "$(CYAN)Python formatting:$(NC)"
	@cd $(PYTHON_DIR) && ruff format --check src tests
	@echo ""
	@echo "$(CYAN)TypeScript formatting:$(NC)"
	@cd $(TS_DIR) && pnpm format:check || pnpm prettier --check "src/**/*.ts" "tests/**/*.ts"
	@echo "$(GREEN)✓ Formatting check passed$(NC)"

type-check: ## Run type checkers (mypy + tsc)
	@echo "$(BLUE)Running type checkers...$(NC)"
	@$(MAKE) type-check-python
	@$(MAKE) type-check-typescript
	@echo "$(GREEN)✓ Type checking passed$(NC)"

type-check-python: ## Run Python type checker (mypy)
	@echo "$(BLUE)Running Python type checker...$(NC)"
	@cd $(PYTHON_DIR) && mypy src
	@echo "$(GREEN)✓ Python type checking passed$(NC)"

type-check-typescript: ## Run TypeScript type checker (tsc)
	@echo "$(BLUE)Running TypeScript type checker...$(NC)"
	@cd $(TS_DIR) && pnpm exec tsc --noEmit
	@echo "$(GREEN)✓ TypeScript type checking passed$(NC)"

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CI Commands
#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ci: ## Run full CI suite (lint + type-check + test + coverage)
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║$(NC)  $(CYAN)Running Full CI Suite$(NC)                                $(BLUE)║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@$(MAKE) ci-python
	@$(MAKE) ci-typescript
	@echo ""
	@echo "$(GREEN)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║$(NC)  $(GREEN)✓ All CI checks passed!$(NC)                              $(GREEN)║$(NC)"
	@echo "$(GREEN)╚════════════════════════════════════════════════════════════╝$(NC)"

ci-python: ## Run Python CI checks
	@echo "$(CYAN)▶ Python CI Pipeline$(NC)"
	@echo "$(YELLOW)  [1/4] Formatting check...$(NC)"
	@cd $(PYTHON_DIR) && ruff format --check src tests
	@echo "$(YELLOW)  [2/4] Linting...$(NC)"
	@cd $(PYTHON_DIR) && ruff check src tests
	@echo "$(YELLOW)  [3/4] Type checking...$(NC)"
	@cd $(PYTHON_DIR) && mypy src
	@echo "$(YELLOW)  [4/4] Tests with coverage...$(NC)"
	@cd $(PYTHON_DIR) && pytest --cov=automagik_telemetry --cov-report=term-missing --cov-fail-under=100 -x -q
	@echo "$(GREEN)  ✓ Python CI passed$(NC)"
	@echo ""

ci-typescript: ## Run TypeScript CI checks
	@echo "$(CYAN)▶ TypeScript CI Pipeline$(NC)"
	@echo "$(YELLOW)  [1/4] Formatting check...$(NC)"
	@cd $(TS_DIR) && pnpm prettier --check "src/**/*.ts" "tests/**/*.ts" || pnpm format:check
	@echo "$(YELLOW)  [2/4] Linting...$(NC)"
	@cd $(TS_DIR) && pnpm lint
	@echo "$(YELLOW)  [3/4] Type checking...$(NC)"
	@cd $(TS_DIR) && pnpm exec tsc --noEmit
	@echo "$(YELLOW)  [4/4] Tests with coverage...$(NC)"
	@cd $(TS_DIR) && pnpm test -- --coverage --coverageReporters=text
	@echo "$(GREEN)  ✓ TypeScript CI passed$(NC)"
	@echo ""

pre-commit: ## Run pre-commit hooks
	@echo "$(BLUE)Running pre-commit hooks...$(NC)"
	@if command -v pre-commit > /dev/null; then \
		pre-commit run --all-files; \
		echo "$(GREEN)✓ Pre-commit checks passed$(NC)"; \
	else \
		echo "$(YELLOW)⚠ pre-commit not installed, running manual checks...$(NC)"; \
		$(MAKE) format-check && $(MAKE) lint && $(MAKE) type-check; \
	fi

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Dependencies & Build Commands
#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

install: ## Install all dependencies (Python + TypeScript)
	@echo "$(BLUE)Installing all dependencies...$(NC)"
	@$(MAKE) install-python
	@$(MAKE) install-typescript
	@echo "$(GREEN)✓ All dependencies installed$(NC)"

install-python: ## Install Python dependencies
	@echo "$(BLUE)Installing Python dependencies...$(NC)"
	@cd $(PYTHON_DIR) && pip install -e ".[dev]"
	@echo "$(GREEN)✓ Python dependencies installed$(NC)"

install-typescript: ## Install TypeScript dependencies
	@echo "$(BLUE)Installing TypeScript dependencies...$(NC)"
	@cd $(TS_DIR) && pnpm install
	@echo "$(GREEN)✓ TypeScript dependencies installed$(NC)"

install-dev: ## Install development tools (pre-commit, etc.)
	@echo "$(BLUE)Installing development tools...$(NC)"
	@if command -v pre-commit > /dev/null; then \
		pre-commit install; \
		echo "$(GREEN)✓ Pre-commit hooks installed$(NC)"; \
	else \
		echo "$(YELLOW)⚠ pre-commit not found, skipping...$(NC)"; \
	fi

update-deps: ## Update all dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	@echo "$(CYAN)Updating Python dependencies:$(NC)"
	@cd $(PYTHON_DIR) && pip install --upgrade -e ".[dev]"
	@echo ""
	@echo "$(CYAN)Updating TypeScript dependencies:$(NC)"
	@cd $(TS_DIR) && pnpm update
	@echo "$(GREEN)✓ Dependencies updated$(NC)"

build: ## Build both SDKs
	@echo "$(BLUE)Building all SDKs...$(NC)"
	@$(MAKE) build-python
	@$(MAKE) build-typescript
	@echo "$(GREEN)✓ All builds completed$(NC)"

build-python: ## Build Python package
	@echo "$(BLUE)Building Python package...$(NC)"
	@cd $(PYTHON_DIR) && python -m build
	@echo "$(GREEN)✓ Python package built$(NC)"

build-typescript: ## Build TypeScript package
	@echo "$(BLUE)Building TypeScript package...$(NC)"
	@cd $(TS_DIR) && pnpm build
	@echo "$(GREEN)✓ TypeScript package built$(NC)"

clean: ## Clean all build artifacts
	@echo "$(BLUE)Cleaning all build artifacts...$(NC)"
	@$(MAKE) clean-python
	@$(MAKE) clean-typescript
	@echo "$(GREEN)✓ All artifacts cleaned$(NC)"

clean-python: ## Clean Python build artifacts
	@echo "$(BLUE)Cleaning Python artifacts...$(NC)"
	@cd $(PYTHON_DIR) && rm -rf build/ dist/ *.egg-info .pytest_cache/ .coverage htmlcov/ .mypy_cache/ .ruff_cache/
	@find $(PYTHON_DIR) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Python artifacts cleaned$(NC)"

clean-typescript: ## Clean TypeScript build artifacts
	@echo "$(BLUE)Cleaning TypeScript artifacts...$(NC)"
	@cd $(TS_DIR) && rm -rf dist/ coverage/ .tsbuildinfo
	@echo "$(GREEN)✓ TypeScript artifacts cleaned$(NC)"

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Infrastructure Commands
#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

infra-start: ## Start local telemetry infrastructure
	@echo "$(BLUE)Starting telemetry infrastructure...$(NC)"
	@cd $(INFRA_DIR) && $(MAKE) start
	@echo "$(GREEN)✓ Infrastructure started$(NC)"
	@echo ""
	@echo "$(YELLOW)Run 'make infra-health' to check service status$(NC)"

infra-stop: ## Stop infrastructure services
	@echo "$(BLUE)Stopping infrastructure...$(NC)"
	@cd $(INFRA_DIR) && $(MAKE) stop
	@echo "$(GREEN)✓ Infrastructure stopped$(NC)"

infra-health: ## Check infrastructure health
	@echo "$(BLUE)Checking infrastructure health...$(NC)"
	@cd $(INFRA_DIR) && $(MAKE) health

infra-logs: ## View infrastructure logs
	@echo "$(BLUE)Viewing infrastructure logs...$(NC)"
	@cd $(INFRA_DIR) && $(MAKE) logs

infra-clean: ## Clean infrastructure data (WARNING: destructive!)
	@echo "$(RED)⚠  WARNING: This will delete all telemetry data!$(NC)"
	@cd $(INFRA_DIR) && $(MAKE) clean
