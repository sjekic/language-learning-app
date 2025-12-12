# Makefile for Language Learning App

.PHONY: help install dev build start stop clean test deploy

# Default target
help:
	@echo "Language Learning App - Development Commands"
	@echo "============================================="
	@echo "make install     - Install all dependencies"
	@echo "make dev         - Start development environment"
	@echo "make dev-local   - Start frontend + all FastAPI services locally (uvicorn + Vite)"
	@echo "make build       - Build all Docker images"
	@echo "make start       - Start all services"
	@echo "make stop        - Stop all services"
	@echo "make clean       - Clean up containers and volumes"
	@echo "make logs        - View logs from all services"
	@echo "make test        - Run tests"
	@echo "make db-init     - Initialize database schema"
	@echo "make db-shell    - Open PostgreSQL shell"
	@echo "make deploy      - Deploy to Azure"

# Install dependencies
install:
	@echo "📦 Installing frontend dependencies..."
	cd frontend && npm install
	@echo "📦 Installing backend dependencies..."
	cd services/auth-service && pip install -r requirements.txt
	cd services/user-service && pip install -r requirements.txt
	cd services/book-service && pip install -r requirements.txt
	cd services/translation-service && pip install -r requirements.txt
	@echo "✅ All dependencies installed!"

# Start development environment
dev:
	@echo "🚀 Starting development environment..."
	docker-compose up --build

# Start local dev environment (no docker; uses uvicorn for services + Vite for frontend)
dev-local:
	@bash scripts/dev-fullstack.sh

# Build Docker images
build:
	@echo "🐳 Building Docker images..."
	docker-compose build

# Start services in background
start:
	@echo "▶️  Starting all services..."
	docker-compose up -d
	@echo "✅ Services started!"
	@echo "Frontend: http://localhost:5173"
	@echo "Auth Service: http://localhost:8001"
	@echo "User Service: http://localhost:8002"
	@echo "Book Service: http://localhost:8003"
	@echo "Translation Service: http://localhost:8004"

# Stop services
stop:
	@echo "⏹️  Stopping all services..."
	docker-compose down
	@echo "✅ Services stopped!"

# Clean up
clean:
	@echo "🧹 Cleaning up containers and volumes..."
	docker-compose down -v
	docker system prune -f
	@echo "✅ Cleanup complete!"

# View logs
logs:
	docker-compose logs -f

# View logs for specific service
logs-auth:
	docker-compose logs -f auth-service

logs-user:
	docker-compose logs -f user-service

logs-book:
	docker-compose logs -f book-service

logs-translation:
	docker-compose logs -f translation-service

logs-db:
	docker-compose logs -f postgres

# Run tests
test:
	@echo "🧪 Running tests..."
	cd frontend && npm run test
	@echo "✅ Tests complete!"

# Initialize database
db-init:
	@echo "🗄️  Initializing database..."
	docker exec -i language-learning-db psql -U postgres -d language_learning < database/init.sql
	@echo "✅ Database initialized!"

# Open database shell
db-shell:
	docker exec -it language-learning-db psql -U postgres -d language_learning

# Deploy to Azure
deploy:
	@echo "☁️  Deploying to Azure..."
	cd azure && chmod +x deploy.sh && ./deploy.sh

# Check service health
health:
	@echo "🏥 Checking service health..."
	@curl -s http://localhost:8001/ | jq . || echo "❌ Auth service down"
	@curl -s http://localhost:8002/ | jq . || echo "❌ User service down"
	@curl -s http://localhost:8003/ | jq . || echo "❌ Book service down"
	@curl -s http://localhost:8004/ | jq . || echo "❌ Translation service down"

# Restart a specific service
restart-auth:
	docker-compose restart auth-service

restart-user:
	docker-compose restart user-service

restart-book:
	docker-compose restart book-service

restart-translation:
	docker-compose restart translation-service

# Development frontend
dev-frontend:
	cd frontend && npm run dev

# Format code
format:
	@echo "🎨 Formatting code..."
	cd frontend && npm run format
	@echo "✅ Code formatted!"

# Lint code
lint:
	@echo "🔍 Linting code..."
	cd frontend && npm run lint
	@echo "✅ Linting complete!"

