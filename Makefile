.PHONY: help build up down logs clean install test lint

# Default target
help:
	@echo "Available commands:"
	@echo "  make build       - Build all Docker images"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make logs        - View logs from all services"
	@echo "  make clean       - Clean up containers and volumes"
	@echo "  make install     - Install dependencies locally"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linters"
	@echo "  make process-data - Run data processing pipeline"

# Docker commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	rm -rf vector-db/indices/*
	rm -rf data/processed/*

# Development commands
install:
	cd backend && pip install -r requirements.txt
	cd data-pipeline && pip install -r requirements.txt
	cd ui/brandbastion-challenge && npm install

# Run specific services
backend:
	docker-compose up -d backend redis

frontend:
	docker-compose up -d frontend

data-pipeline:
	docker-compose run --rm data-pipeline

# Process sample data
process-data:
	@echo "Creating sample data directories..."
	mkdir -p data/raw/pdfs data/raw/comments
	@echo "Running data processing pipeline..."
	docker-compose run --rm data-pipeline

# Utility commands
shell-backend:
	docker-compose exec backend /bin/bash

shell-data:
	docker-compose exec data-pipeline /bin/bash

# Testing
test:
	@echo "Running backend tests..."
	docker-compose run --rm backend pytest
	@echo "Running frontend tests..."
	docker-compose run --rm frontend npm test

# Linting
lint:
	@echo "Linting backend..."
	docker-compose run --rm backend pylint api agents chains
	@echo "Linting frontend..."
	docker-compose run --rm frontend npm run lint