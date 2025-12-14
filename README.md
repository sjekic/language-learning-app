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
