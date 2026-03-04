.DEFAULT_GOAL := help

COMPOSE_FILE ?= bfd9000_web/docker-compose.yml

.PHONY: help build-test-docker run-test-docker mock-bfd9010

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_-]+:.*##/ {printf "%-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build-test-docker: ## Build test Docker image with compose
	docker compose -f $(COMPOSE_FILE) build

run-test-docker: ## Run test Docker stack with compose
	docker compose -f $(COMPOSE_FILE) up

mock-bfd9010: ## Start the mock BFD9010 scanner service on port 5000
	python dev_tools/mock_bfd9010.py --host localhost
