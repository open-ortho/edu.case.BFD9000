.DEFAULT_GOAL := help

COMPOSE_FILE ?= bfd9000_web/docker-compose.yml

.PHONY: help build-test-docker run-test-docker

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_-]+:.*##/ {printf "%-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build-test-docker: ## Build test Docker image with compose
	docker compose -f $(COMPOSE_FILE) build

run-test-docker: ## Run test Docker stack with compose
	docker compose -f $(COMPOSE_FILE) up
