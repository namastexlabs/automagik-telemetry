.PHONY: help start stop restart logs status clean test health dashboard

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Automagik Telemetry Infrastructure Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Available commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Quick Start:$(NC)"
	@echo "  1. $(YELLOW)make start$(NC)       - Start all services"
	@echo "  2. $(YELLOW)make health$(NC)      - Check service health"
	@echo "  3. $(YELLOW)make dashboard$(NC)   - Open Grafana dashboard"
	@echo "  4. $(YELLOW)make test$(NC)        - Send test telemetry data"
	@echo ""

start: ## Start all telemetry infrastructure services
	@echo "$(BLUE)Starting Automagik Telemetry Infrastructure...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo ""
	@echo "Services:"
	@echo "  • ClickHouse:  http://localhost:8123"
	@echo "  • Collector:   http://localhost:4318 (HTTP) | http://localhost:4317 (gRPC)"
	@echo "  • Grafana:     http://localhost:3000 (admin/admin)"
	@echo ""
	@echo "Run '$(YELLOW)make health$(NC)' to check service status"
	@echo "Run '$(YELLOW)make logs$(NC)' to view service logs"

stop: ## Stop all services
	@echo "$(BLUE)Stopping services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

restart: ## Restart all services
	@echo "$(BLUE)Restarting services...$(NC)"
	docker-compose restart
	@echo "$(GREEN)✓ Services restarted$(NC)"

logs: ## Tail logs from all services
	docker-compose logs -f --tail=100

logs-clickhouse: ## Tail ClickHouse logs
	docker-compose logs -f --tail=100 clickhouse

logs-collector: ## Tail Collector logs
	docker-compose logs -f --tail=100 collector

logs-grafana: ## Tail Grafana logs
	docker-compose logs -f --tail=100 grafana

status: ## Show status of all services
	@echo "$(BLUE)Service Status:$(NC)"
	@docker-compose ps

health: ## Check health of all services
	@echo "$(BLUE)Checking service health...$(NC)"
	@echo ""
	@echo -n "$(YELLOW)ClickHouse:$(NC) "
	@if curl -s http://localhost:8123/ping > /dev/null 2>&1; then \
		echo "$(GREEN)✓ Healthy$(NC)"; \
	else \
		echo "$(RED)✗ Unhealthy$(NC)"; \
	fi
	@echo -n "$(YELLOW)Collector:$(NC)  "
	@if curl -s http://localhost:4318/v1/traces > /dev/null 2>&1; then \
		echo "$(GREEN)✓ Healthy$(NC)"; \
	else \
		echo "$(RED)✗ Unhealthy$(NC)"; \
	fi
	@echo -n "$(YELLOW)Grafana:$(NC)    "
	@if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then \
		echo "$(GREEN)✓ Healthy$(NC)"; \
	else \
		echo "$(RED)✗ Unhealthy$(NC)"; \
	fi
	@echo ""

dashboard: ## Open Grafana dashboard in browser
	@echo "$(BLUE)Opening Grafana dashboard...$(NC)"
	@echo "URL: http://localhost:3000"
	@echo "Login: admin / admin"
	@if command -v xdg-open > /dev/null; then \
		xdg-open http://localhost:3000; \
	elif command -v open > /dev/null; then \
		open http://localhost:3000; \
	else \
		echo "Please open http://localhost:3000 in your browser"; \
	fi

test: ## Send test telemetry data
	@echo "$(BLUE)Sending test telemetry data...$(NC)"
	@./scripts/send-test-data.sh
	@echo "$(GREEN)✓ Test data sent$(NC)"
	@echo "View data in Grafana: $(YELLOW)make dashboard$(NC)"

query: ## Run interactive ClickHouse query
	@echo "$(BLUE)Connecting to ClickHouse...$(NC)"
	docker-compose exec clickhouse clickhouse-client --database=telemetry

query-traces: ## Show recent traces
	@echo "$(BLUE)Recent traces (last 10):$(NC)"
	@docker-compose exec clickhouse clickhouse-client --database=telemetry --query="SELECT timestamp, project_name, span_name, status_code FROM traces ORDER BY timestamp DESC LIMIT 10"

query-stats: ## Show telemetry statistics
	@echo "$(BLUE)Telemetry Statistics:$(NC)"
	@docker-compose exec clickhouse clickhouse-client --database=telemetry --query="SELECT project_name, count() as events, countIf(status_code != 'OK') as errors FROM traces GROUP BY project_name"

clean: ## Stop services and remove all data (WARNING: destructive!)
	@echo "$(RED)WARNING: This will delete all telemetry data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(BLUE)Stopping services and removing data...$(NC)"; \
		docker-compose down -v; \
		echo "$(GREEN)✓ All data removed$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

reset: ## Reset all data but keep services running
	@echo "$(YELLOW)Resetting telemetry data...$(NC)"
	docker-compose exec clickhouse clickhouse-client --database=telemetry --query="TRUNCATE TABLE traces"
	docker-compose exec clickhouse clickhouse-client --database=telemetry --query="TRUNCATE TABLE metrics_hourly"
	@echo "$(GREEN)✓ Data reset$(NC)"

backup: ## Backup ClickHouse data
	@echo "$(BLUE)Creating backup...$(NC)"
	@mkdir -p ./backups
	docker-compose exec clickhouse clickhouse-client --database=telemetry --query="SELECT * FROM traces FORMAT CSV" > ./backups/traces_$(shell date +%Y%m%d_%H%M%S).csv
	@echo "$(GREEN)✓ Backup created in ./backups/$(NC)"

update: ## Update all Docker images
	@echo "$(BLUE)Updating Docker images...$(NC)"
	docker-compose pull
	@echo "$(GREEN)✓ Images updated$(NC)"
	@echo "Run '$(YELLOW)make restart$(NC)' to use updated images"

# Development helpers
dev-python: ## Run Python example against local infrastructure
	@echo "$(BLUE)Running Python example...$(NC)"
	cd ../examples/python && AUTOMAGIK_TELEMETRY_ENDPOINT=http://localhost:4318/v1/traces python main.py

dev-typescript: ## Run TypeScript example against local infrastructure
	@echo "$(BLUE)Running TypeScript example...$(NC)"
	cd ../examples/typescript && AUTOMAGIK_TELEMETRY_ENDPOINT=http://localhost:4318/v1/traces npm start
