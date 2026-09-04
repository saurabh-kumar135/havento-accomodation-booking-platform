# 🏡 Heaven_Python - Modern Full-Stack Accommodation Platform

A high-performance, full-stack vacation rental platform featuring a **FastAPI (Python 3.12)** async backend, **MongoDB Atlas (Beanie ODM)**, an intelligent **AI Travel Concierge (Groq + RAG Memory)**, and a **React (Vite + TailwindCSS)** frontend.

---

## ⚡ Key Features

- **High-Performance Async Backend**: Built with FastAPI and async Motor/Beanie ODM for sub-millisecond response times.
- **AI Travel Concierge**: Integrated LangChain & Groq LLM with 384-dimensional semantic memory retrieval (RAG) for personalized guest recommendations.
- **Enterprise-Grade Email Delivery**: Gmail OAuth2 & SMTP transactional mail engine sending OTPs and password resets to any recipient.
- **Complete Booking Workflow**: Real-time property availability, price calculation, and date management.
- **Host Dashboard**: Property listing management with multipart image uploads.
- **Docker & Compose**: Production-ready containerization for 1-click deployment.
- **CI/CD Pipeline**: GitHub Actions for automated linting, test suites (`pytest`), and Docker image builds.

---

## 🏗️ Architecture

```text
Heaven_Python/
├── backend/                  # FastAPI Python Application
│   ├── app/
│   │   ├── core/             # Configuration, Database, Security & Email
│   │   ├── models/           # Beanie MongoDB Documents (User, Home, Booking)
│   │   ├── schemas/          # Pydantic validation schemas
│   │   ├── routers/          # API Route Controllers (Auth, Store, Host, Agent)
│   │   ├── services/         # AI Agent and RAG Memory services
│   │   └── main.py           # FastAPI Application Entrypoint
│   ├── Dockerfile            # Production Backend Dockerfile
│   ├── requirements.txt      # Python Dependencies
│   └── tests/                # Pytest Test Suite
├── client/                   # React + Vite Frontend
│   ├── Dockerfile            # Nginx Multi-stage Dockerfile
│   └── src/                  # React Application Components & Pages
├── docker-compose.yml        # Multi-Container Orchestration
└── .github/workflows/        # Automated CI/CD Workflows
```

---

## 🚀 Quick Start Guide

### 1. Run with Docker Compose (Recommended)

```bash
cd Heaven_Python
docker compose up --build
```
- **Frontend**: `http://localhost:80`
- **Backend API**: `http://localhost:3009`
- **Interactive API Docs (Swagger)**: `http://localhost:3009/docs`

---

### 2. Local Development Setup

#### Backend Setup:
```bash
cd Heaven_Python/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --port 3009 --reload
```

#### Frontend Setup:
```bash
cd Heaven_Python/client
npm install
npm run dev
```

---

## 🧪 Running Tests

```bash
cd Heaven_Python/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests -v
```

---

## 📜 API Documentation

Once the backend is running, visit **`http://localhost:3009/docs`** for interactive Swagger UI documentation and endpoint testing.
