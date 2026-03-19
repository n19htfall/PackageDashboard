SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help install install-backend install-frontend dev dev-backend dev-frontend build-frontend

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-18s %s\n", $$1, $$2}'

install: ## Install backend and frontend dependencies
	./scripts/bootstrap.sh

install-backend: ## Install backend dependencies with Poetry
	cd backend && poetry install --no-root

install-frontend: ## Install frontend dependencies with pnpm
	pnpm --dir frontend install

dev: ## Start backend and frontend together from the repository root
	./scripts/dev.sh

dev-backend: ## Start only the FastAPI backend in reload mode
	cd backend && poetry run python -m pkgdash.serve --reload

dev-frontend: ## Start only the Vite frontend
	pnpm --dir frontend dev

build-frontend: ## Build the frontend bundle
	pnpm --dir frontend build
