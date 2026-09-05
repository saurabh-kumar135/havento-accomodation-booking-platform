# 🏡 HavenTo - Accommodation Booking Platform (Python Stack)

[![CI/CD Pipeline](https://github.com/saurabh-kumar135/havento-accomodation-booking-platform/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/saurabh-kumar135/havento-accomodation-booking-platform/actions/workflows/ci-cd.yml)
[![EC2 Deployment](https://github.com/saurabh-kumar135/havento-accomodation-booking-platform/actions/workflows/deploy.yml/badge.svg)](https://github.com/saurabh-kumar135/havento-accomodation-booking-platform/actions/workflows/deploy.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modern, high-performance vacation rental & accommodation booking platform converted from Node.js/Express to **Python FastAPI (3.12)** while preserving 100% architectural parity with the original codebase.

Featuring an **autonomous AI Travel Concierge** (Groq LLM + MongoDB Tool Calling + RAG Memory), **MongoDB Atlas & GridFS** photo streaming, and a production **React (Vite + TailwindCSS)** client.

---

## 🌐 Live Production Deployments

* **Frontend Web App (Vercel)**: [**https://havento.vercel.app**](https://havento.vercel.app)
* **Backend API & Swagger Docs (AWS EC2)**: [**https://havento.duckdns.org/docs**](https://havento.duckdns.org/docs)
* **API Health Status**: [**https://havento.duckdns.org/api/health**](https://havento.duckdns.org/api/health)

---

## ⚡ Key Highlights

* **1:1 MVC Architectural Mirroring**: Directly mirrors the original Node.js/Express layout (`controllers/`, `routes/`, `models/`, `middleware/`, `services/`, `utils/`, `rag_service/`, `app.py`).
* **Autonomous AI Travel Concierge**: Powered by Groq LLM with function/tool calling (`searchHomes`, `getHomeDetails`, `getUserBookings`) and real-time MongoDB search across any location or property.
* **Dual-Tier Image Streaming**: Binary media served directly from MongoDB Atlas GridFS buckets (`photos.files`/`photos.chunks`) with automatic fallback to high-resolution CDNs.
* **Complete Booking & Cancellation Lifecycle**: Real-time date reservation, dynamic price calculation, and strict 24-hour cancellation policies with verified reasoning.
* **Enterprise Authentication**: Bcrypt password hashing, JWT sessions, OTP email verification via Gmail SMTP/OAuth2, and password reset workflows.
* **Containerized Deployment**: Multi-stage Docker setup with Nginx reverse proxy and automated EC2 deployment via GitHub Actions.

---

## 🏗️ Architecture & Codebase Map

```text
havento-accomodation-booking-platform/
├── backend/                              # Python FastAPI Application
│   ├── app.py                            # Server entrypoint, CORS, GridFS streaming & routes
│   ├── config.py                         # Environment configurations & defaults
│   ├── controllers/                      # Request handling logic
│   │   ├── authController.py             # Login, signup, sessions, Google auth
│   │   ├── emailVerificationController.py# 6-digit OTP dispatch & validation
│   │   ├── passwordResetController.py    # Token generation & password reset
│   │   ├── storeController.py            # Home browsing, favourites & bookings
│   │   ├── hostController.py             # Host property creation, edits & reservations
│   │   └── agentController.py            # AI concierge chat endpoints & memory clear
│   ├── routes/                           # Router definitions mapping endpoints to controllers
│   │   ├── authRouter.py                 # /api/auth/*
│   │   ├── emailVerificationRoutes.py    # /api/auth/verify-otp, resend-otp
│   │   ├── passwordResetRoutes.py        # /api/auth/reset-password/*
│   │   ├── storeRouter.py                # /api/homes, /api/store/*
│   │   ├── hostRouter.py                 # /api/host/*
│   │   └── agentRouter.py                # /api/agent/*
│   ├── models/                           # Beanie ODM MongoDB Document Schemas
│   │   ├── user.py                       # User profile & credentials
│   │   ├── home.py                       # Property listings & amenities
│   │   ├── booking.py                    # Reservations & cancellation policies
│   │   ├── pendingVerification.py        # Pending registration OTP records
│   │   └── passwordReset.py              # Password reset tokens
│   ├── middleware/                       # Security & authentication middleware
│   │   └── auth.py                       # JWT token verification (User & Host guards)
│   ├── services/                         # Business & AI logic
│   │   └── agentService.py               # Groq LLM tool-calling loop & dynamic search
│   ├── utils/                            # Shared utilities
│   │   ├── databaseUtil.py               # MongoDB Atlas connection & GridFS bucket
│   │   ├── emailService.py               # Gmail OAuth2 & SMTP transactional email
│   │   └── security.py                   # Bcrypt hashing & JWT token handling
│   ├── rag_service/                      # RAG vector similarity & memory persistence
│   │   └── memory.py                     # Context-aware user conversation memory
│   ├── tests/                            # Pytest test suite
│   ├── Dockerfile                        # Production backend container definition
│   └── requirements.txt                  # Lean production dependencies
├── client/                               # React + Vite Frontend
│   ├── Dockerfile                        # Production Nginx multi-stage build
│   ├── nginx.conf                        # Reverse proxy for /api and /uploads + SPA routing
│   └── src/                              # React components, state & pages
├── docker-compose.yml                    # Multi-container local & cloud orchestration
└── .github/workflows/                    # CI/CD automation pipelines
    ├── ci-cd.yml                         # Automated Flake8 linting, Pytest, and Docker build
    └── deploy.yml                        # Automated deployment to AWS EC2 via SSH
```

---

## 🚀 Quick Start Guide

### 1. Run with Docker Compose (Recommended)

To run the complete full-stack application (Frontend + Backend + Proxy) locally:

```bash
# Clone the repository
git clone https://github.com/saurabh-kumar135/havento-accomodation-booking-platform.git
cd havent-accomodation-booking-platform

# Set up environment variables
cp backend/.env.example backend/.env

# Build and start all services
docker compose up -d --build
```

Access points:
* **Web UI**: [http://localhost](http://localhost)
* **FastAPI Docs (Swagger UI)**: [http://localhost:3009/docs](http://localhost:3009/docs)
* **Backend Health Check**: [http://localhost/api/health](http://localhost/api/health)

---

### 2. Manual Local Development

#### Backend Setup:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env    # Configure your MongoDB URI and API keys
uvicorn app:app --host 0.0.0.0 --port 3009 --reload
```

#### Frontend Setup:
```bash
cd client
npm install
npm run dev
```

---

## 🧪 Testing

Execute the automated test suite verifying health endpoints, authentication flows, and AI concierge search:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest tests -v
```

---

## 🤖 AI Travel Concierge Capabilities

The HavenTo Assistant is equipped with real-time tool calling and semantic memory:

* **Location Search**: Type queries like *"Find stays in Taharpur"*, *"Show beach villas in Goa"*, or *"Best homes in Mumbai under ₹10,000"*.
* **Listing Inspection**: Inspect specific properties with *"Tell me more about Saurabh's home"* to get full details, ratings, and amenities.
* **Reservation Assistance**: Guides users through booking policies, check-in requirements, and cancellation rules.
* **Domain Guardrails**: Strict policy ensuring the assistant focuses solely on HavenTo accommodation services.

---

## 📦 Deployment Architecture

* **AWS EC2 Production Server**:
  - Ubuntu 24.04 LTS host with Python 3.12 virtual environment.
  - Managed via `systemd` daemon: `havento-api.service`.
  - Nginx reverse proxy with automated Let's Encrypt SSL on `https://havento.duckdns.org`.
* **Vercel Production Frontend**:
  - Continuous deployment connected to the React client repository.
  - Automated edge asset compression and global CDN distribution.
* **GitHub Actions CI/CD**:
  - Continuous Integration: Checks code formatting, linting (`flake8`), and executes `pytest` tests on every push.
  - Continuous Deployment: Automatically SSHs into AWS EC2, pulls the latest code, and restarts the service.

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
