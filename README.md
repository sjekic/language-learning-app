# Language Learning App - AI-Powered Story Platform

A full-stack language learning application that generates personalized AI stories in multiple languages, helping users learn through immersive reading experiences.

## 🌟 Features

- **AI Story Generation**: Generate custom stories in 6+ languages (Spanish, French, German, Italian, Japanese, Chinese)
- **Adaptive Difficulty**: Stories tailored to your language level (A1-C1)
- **Genre Selection**: Choose from Fantasy, Sci-Fi, Adventure, Mystery, and Slice of Life
- **Interactive Reading**: Click on words for instant translations
- **Vocabulary Tracking**: Automatically saves words you look up
- **Progress Tracking**: Monitor your reading progress and favorite books
- **Beautiful UI**: Modern, responsive design with smooth animations

## 🏗️ Architecture

### Microservices Architecture

```
Frontend (React + TypeScript + Vite)
         │
         ├─────► Auth Service (FastAPI) - Authentication & JWT
         ├─────► User Service (FastAPI) - User profiles & stats
         ├─────► Book Service (FastAPI) - Story generation & library
         └─────► Translation Service (FastAPI) - Word lookup & vocabulary
                        │
                        ├─────► Azure Container Jobs (Story generation)
                        ├─────► Azure Blob Storage (Book content & covers)
                        ├─────► Azure SQL (PostgreSQL)
                        └─────► Linguee API (Translations)
```

### Technology Stack

**Frontend:**
- React 18 + TypeScript
- Vite (build tool)
- TailwindCSS (styling)
- React Router (navigation)

**Backend:**
- Python 3.11
- FastAPI (4 microservices)
- AsyncPG (PostgreSQL driver)
- JWT authentication

**Cloud Infrastructure:**
- Azure Container Apps
- Azure Blob Storage
- Azure Database for PostgreSQL
- Azure Container Jobs
- Azure Container Registry

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- Docker & Docker Compose
- Azure CLI (for deployment)

### Local Development

#### 1. Clone the repository

```bash
git clone <repository-url>
cd language-learning-app
```

#### 2. Start Backend Services

```bash
# Start all services with Docker Compose
docker-compose up --build

# Services will be available at:
# - Auth Service: http://localhost:8001
# - User Service: http://localhost:8002
# - Book Service: http://localhost:8003
# - Translation Service: http://localhost:8004
# - PostgreSQL: localhost:5432
```

#### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev

# Frontend will be available at:
# http://localhost:5173
```

#### 4. Initialize Database

```bash
# Apply database schema
docker exec -i language-learning-db psql -U postgres -d language_learning < database/init.sql
```

### Environment Variables

Create `.env` files in the root directory:

```bash
# .env (root)
JWT_SECRET_KEY=your-super-secret-key-change-in-production
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/language_learning

# Azure Configuration (for production)
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_RESOURCE_GROUP=language-learning-rg
AZURE_STORAGE_CONNECTION_STRING=your-storage-connection-string
AZURE_STORAGE_ACCOUNT_NAME=your-storage-account
```

## 📦 Deployment to Azure

### Automated Deployment

```bash
cd azure
chmod +x deploy.sh
./deploy.sh
```

This script will:
1. Create Azure Resource Group
2. Create Azure Container Registry
3. Set up PostgreSQL database
4. Create Azure Storage (for book content)
5. Build and push Docker images
6. Deploy all microservices to Azure Container Apps
7. Output service URLs

### Manual Deployment

See detailed instructions in `/azure/README.md`

## 📖 API Documentation

Each microservice provides interactive API documentation:

- Auth Service: http://localhost:8001/docs
- User Service: http://localhost:8002/docs
- Book Service: http://localhost:8003/docs
- Translation Service: http://localhost:8004/docs

### Key Endpoints

**Authentication:**
```
POST /api/auth/signup     - Register new user
POST /api/auth/login      - Login and get JWT token
POST /api/auth/verify     - Verify token
```

**Books:**
```
POST /api/books/generate  - Generate new story (triggers Azure Job)
GET  /api/books           - Get user's library
GET  /api/books/{id}      - Get book details
GET  /api/books/{id}/content - Get book pages
DELETE /api/books/{id}    - Delete book
```

**Translation & Vocabulary:**
```
GET  /api/translate       - Translate a word
POST /api/vocabulary      - Save word to vocabulary
GET  /api/vocabulary      - Get saved words
GET  /api/vocabulary/stats - Get learning statistics
```

## 🗄️ Database Schema

```sql
users               - User accounts
auth_credentials    - Password hashes
books               - Generated stories
user_books          - User-book relationships
vocabulary          - Tracked vocabulary words
```

Full schema available in `/database/init.sql`

## 🔧 Development

### Project Structure

```
language-learning-app/
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/   # Reusable UI components
│   │   ├── pages/        # Page components
│   │   ├── layouts/      # Layout wrappers
│   │   └── lib/          # Utilities
│   └── public/
├── services/             # Backend microservices
│   ├── auth-service/
│   ├── user-service/
│   ├── book-service/
│   └── translation-service/
├── database/             # Database schemas
├── azure/                # Azure deployment configs
├── docker-compose.yml    # Local development
└── README.md
```

### Running Tests

```bash
# Frontend tests
cd frontend
npm run test

# Backend tests (TODO: Add pytest)
cd services/auth-service
pytest
```

### Adding a New Feature

1. Update the relevant microservice
2. Update database schema if needed
3. Update frontend components
4. Test locally with Docker Compose
5. Deploy to Azure

## 🎯 Roadmap

### Phase 1: Core Features ✅
- [x] User authentication
- [x] Story generation (placeholder)
- [x] Story library
- [x] Word translation
- [x] Vocabulary tracking

### Phase 2: Azure Integration (Current)
- [x] Azure Container Apps deployment
- [x] Azure Blob Storage for books
- [x] PostgreSQL database
- [ ] Azure Container Jobs for AI generation
- [ ] Azure OpenAI integration

### Phase 3: Enhanced Features
- [ ] Audio narration of stories
- [ ] Progress tracking and streaks
- [ ] Spaced repetition for vocabulary
- [ ] Social features (share stories)
- [ ] Mobile app (React Native)

### Phase 4: Advanced Features
- [ ] Custom story templates
- [ ] Community-generated content
- [ ] Grammar exercises
- [ ] Speaking practice with AI
- [ ] Achievement system

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [Linguee API](https://linguee-api.fly.dev/) for translations
- Azure for cloud infrastructure
- FastAPI for backend framework
- React for frontend framework

## 📧 Contact

For questions or support, please open an issue on GitHub.

## 🐛 Known Issues

1. **Azure Container Jobs**: Currently a placeholder. Need to implement actual AI story generation worker.
2. **Cover Generation**: Using client-side generation. Should move to backend.
3. **Authentication**: Need to add refresh tokens for better security.
4. **Rate Limiting**: No rate limiting implemented yet.

## 🔐 Security

- Passwords are hashed with bcrypt
- JWT tokens for authentication
- Environment variables for secrets
- Azure Key Vault recommended for production
- CORS configured for trusted origins

## 📊 Monitoring

For production deployment, consider adding:
- Azure Application Insights
- Log Analytics workspace
- Custom metrics and alerts
- Performance monitoring

## 💡 Tips

**Local Development:**
- Use `docker-compose logs -f [service-name]` to view logs
- Access PostgreSQL: `docker exec -it language-learning-db psql -U postgres -d language_learning`
- Rebuild specific service: `docker-compose up -d --build [service-name]`

**Azure Deployment:**
- Monitor costs in Azure Portal
- Use Azure Cost Management for budgets
- Scale services based on load
- Enable auto-scaling for production

---

**Happy Learning! 🎓📚**
