export OLLAMA_HOST=http://localhost:11434
export OLLAMA_MODEL=granite3-moe:latest

# Makefile for Zabbix AI Alert Predictor

.PHONY: help build up down restart logs status logs-ollama logs-app clean install-model test-ollama-api test-ollama shell-ollama shell-app start reset

# Default target
help:
	@echo "Available commands:"
	@echo "  build       		- Build all Docker images"
	@echo "  up          		- Start all containers"
	@echo "  down        		- Stop and remove all containers"
	@echo "  restart     		- Restart all containers"
	@echo "  logs        		- Show logs from all containers"
	@echo "  status      		- Show status of all containers"
	@echo "  logs-ollama 		- Show logs from Ollama container only"
	@echo "  logs-app    		- Show logs from Streamlit app container only"
	@echo "  clean       		- Remove containers, networks, and volumes"
	@echo "  install-model 		- Install and setup the Ollama model"
	@echo "  test-ollama-api 	- Test Ollama API connection"
	@echo "  test-ollama 		- Run comprehensive Ollama test script"
	@echo "  shell-ollama 		- Open shell in Ollama container"
	@echo "  shell-app   		- Open shell in Streamlit app container"
	@echo "  start       		- Quick start: build and run everything"
	@echo "  reset       		- Full reset: clean and start fresh"
	@echo "  generate        	- Generate mock Zabbix data for testing"

# Build all images
build:
	docker-compose build

# Start all containers
up: down
	docker-compose up -d
	@echo "Containers started. Waiting for Ollama to be ready..."
	@sleep 10
	@make install-model

# Stop and remove containers
down:
	docker-compose down

# Restart all containers
restart:
	docker-compose restart

# Show logs from all containers
logs:
	docker-compose logs -f

# Check status of containers
status:
	docker-compose ps

# Show logs from Ollama container
logs-ollama:
	docker-compose logs -f ollama

# Show logs from Streamlit app container
logs-app:
	docker-compose logs -f app

# Clean up everything
clean:
	docker-compose down -v --remove-orphans
	docker system prune -f

# Install and setup the model
install-model:
	@echo "Checking if ollama model is already installed in Ollama container..."
	@if docker exec zabbix_ai_ollama ollama list | grep -q '$(OLLAMA_MODEL)'; then \
		echo "$(OLLAMA_MODEL) model already installed."; \
	else \
		echo "Installing $(OLLAMA_MODEL) model..."; \
		docker exec -it zabbix_ai_ollama ollama pull $(OLLAMA_MODEL) || echo "Model pull failed"; \
		sleep 5; \
	fi
	@echo "Verifying model installation..."
	@docker exec zabbix_ai_ollama ollama list

# Test Ollama API connection
test-ollama-api:
	@echo "Testing Ollama API connection..."
	@curl -s -X POST http://localhost:11434/api/generate \
		-H "Content-Type: application/json" \
		-d '{"model": "$(OLLAMA_MODEL)", "prompt": "Hello, world!", "stream": false}' \
		| jq -r '.response // .error' || echo "API test failed or jq not available"

# Test using Python test script
test-ollama:
	@echo "Running Python test script..."
	@python bin/test_ollama.py

# Open shell in Ollama container
shell-ollama:
	docker exec -it zabbix_ai_ollama /bin/bash

# Open shell in Streamlit app container
shell-app:
	docker exec -it zabbix_ai_app /bin/bash

# Quick start - build and run everything
start: build up

# Full reset - clean and start fresh
reset: clean start

# Generate mock Zabbix data for testing
generate:
	@echo "Generating mock Zabbix data..."
	@python bin/data_generator.py
