# Language Learning App - Microservices

This directory contains all the microservices for the Language Learning Application.

## Architecture Overview

```
┌─────────────────┐
│    Frontend     │
│   (React/TS)    │
└────────┬────────┘
         │
         ├──────────────┬──────────────┬──────────────┐
         │              │              │              │
    ┌────▼────┐   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
    │  Auth   │   │  User   │   │  Book   │   │  Trans  │
    │ Service │   │ Service │   │ Service │   │ Service │
    │  :8001  │   │  :8002  │   │  :8003  │   │  :8004  │
    └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘
         │              │              │              │
         └──────────────┴──────────────┴──────────────┘
                           │
                      ┌────▼────┐
                      │PostgreSQL│
                      │Database │
                      └─────────┘
```

## Services

### 1. Auth Service (Port 8001)
**Responsibility:** User authentication and JWT token management

**Endpoints:**
- `POST /api/auth/signup` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `POST /api/auth/verify` - Verify JWT token validity

**Technologies:**
- FastAPI
- PyJWT
- Bcrypt for password hashing

### 2. User Service (Port 8002)
**Responsibility:** User profile management and statistics

**Endpoints:**
- `GET /api/users/me` - Get current user profile
- `PUT /api/users/me` - Update user profile
- `GET /api/users/me/stats` - Get user statistics
- `DELETE /api/users/me` - Delete user account

**Technologies:**
- FastAPI
- HTTPX for auth service communication

### 3. Book Service (Port 8003)
**Responsibility:** Book generation, library management, and reading

**Endpoints:**
- `POST /api/books/generate` - Trigger AI story generation (Azure Job)
- `GET /api/books/jobs/{job_id}` - Check generation job status
- `GET /api/books` - Get user's book library
- `GET /api/books/{book_id}` - Get book details
- `GET /api/books/{book_id}/content` - Get book content (pages)
- `PUT /api/books/{book_id}` - Update book metadata (favorite, progress)
- `DELETE /api/books/{book_id}` - Delete book

**Technologies:**
- FastAPI
- Azure Container Jobs (for AI story generation)
- Azure Blob Storage (for book content and covers)
- Azure SDK

**Azure Integration:**
- Triggers Azure Container Jobs for long-running AI story generation
- Stores book content (JSON) in Azure Blob Storage
- Stores cover images in separate blob container

### 4. Translation Service (Port 8004)
**Responsibility:** Word translation and vocabulary tracking

**Endpoints:**
- `GET /api/translate` - Translate a word/phrase
- `POST /api/vocabulary` - Save word to vocabulary
- `GET /api/vocabulary` - Get user's vocabulary list
- `DELETE /api/vocabulary/{vocab_id}` - Delete vocabulary word
- `GET /api/vocabulary/stats` - Get vocabulary statistics

**Technologies:**
- FastAPI
- Linguee API integration
- Cachetools for translation caching

## Database Schema

All services connect to the same PostgreSQL database with the following tables:

- `users` - User accounts
- `auth_credentials` - Password hashes
- `books` - Generated books/stories
- `user_books` - User-book relationships (ownership, favorites, progress)
- `vocabulary` - Tracked vocabulary words with translations

## Running Locally

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+

### Option 1: Docker Compose (Recommended)

```bash
# From project root
docker-compose up --build

# Services will be available at:
# - Auth Service: http://localhost:8001
# - User Service: http://localhost:8002
# - Book Service: http://localhost:8003
# - Translation Service: http://localhost:8004
# - PostgreSQL: localhost:5432
```

### Option 2: Manual Setup

Each service can be run independently:

```bash
# 1. Start PostgreSQL
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=language_learning \
  -p 5432:5432 \
  postgres:15-alpine

# 2. Initialize database
psql postgresql://postgres:postgres@localhost:5432/language_learning -f ../database/init.sql

# 3. Start each service
cd services/auth-service
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001

# Repeat for other services (in separate terminals)
```

## Environment Variables

Each service requires the following environment variables:

### All Services
- `DATABASE_URL` - PostgreSQL connection string
- `AUTH_SERVICE_URL` - URL to auth service (for inter-service communication)

### Auth Service
- `JWT_SECRET_KEY` - Secret key for JWT token signing

### Book Service
- `AZURE_SUBSCRIPTION_ID` - Azure subscription ID
- `AZURE_RESOURCE_GROUP` - Azure resource group name
- `AZURE_STORAGE_CONNECTION_STRING` - Azure Storage connection string
- `AZURE_STORAGE_ACCOUNT_NAME` - Storage account name
- `AZURE_STORAGE_CONTAINER_NAME` - Container for book content
- `AZURE_STORAGE_COVER_CONTAINER` - Container for cover images

### Translation Service
- `LINGUEE_API_URL` - Linguee translation API URL

## Development

### Adding a New Endpoint

1. Add the endpoint to the appropriate service's `main.py`
2. Update the service's tests
3. Rebuild the Docker image
4. Update this README with the new endpoint

### Database Migrations

For schema changes:

1. Update `database/init.sql`
2. Create a migration script in `database/migrations/`
3. Apply migrations manually or use a tool like Alembic

### Testing

Each service includes health check endpoints at `/`:

```bash
curl http://localhost:8001/  # Auth service
curl http://localhost:8002/  # User service
curl http://localhost:8003/  # Book service
curl http://localhost:8004/  # Translation service
```

## API Documentation

Each service provides interactive API documentation:

- Auth Service: http://localhost:8001/docs
- User Service: http://localhost:8002/docs
- Book Service: http://localhost:8003/docs
- Translation Service: http://localhost:8004/docs

## Security

- All inter-service communication uses JWT tokens
- Passwords are hashed with bcrypt
- Database credentials stored as environment variables
- Azure credentials managed via Azure Key Vault (in production)
- CORS configured for frontend origin

## Monitoring & Logging

- Health checks configured for each service
- Logs output to stdout (captured by Docker/Azure)
- Consider adding Application Insights for Azure deployment

## Troubleshooting

### Service won't start
1. Check database connection: `psql $DATABASE_URL`
2. Verify environment variables are set
3. Check logs: `docker-compose logs [service-name]`

### Database connection errors
1. Ensure PostgreSQL is running
2. Check DATABASE_URL format
3. Verify network connectivity

### Azure integration not working
1. Verify Azure credentials are configured
2. Check resource group and subscription ID
3. Ensure storage account exists and is accessible

## Next Steps

1. **Implement Azure Container Jobs Worker**
   - Create a separate worker container for AI story generation
   - Integrate with Azure OpenAI
   - Process jobs from the queue

2. **Add API Gateway**
   - Consider using Azure API Management
   - Implement rate limiting
   - Add request/response logging

3. **Implement Caching**
   - Add Redis for session management
   - Cache frequent database queries
   - Cache translation results (already implemented in-memory)

4. **Add Testing**
   - Unit tests for each endpoint
   - Integration tests for service communication
   - Load testing for Azure deployment

5. **CI/CD Pipeline**
   - Automate Docker builds
   - Automated testing
   - Deployment to Azure Container Apps

