# VeriHire AI

**Evidence-backed hiring intelligence — rank candidates by proven engineering signals and multi-layered AI analysis, not resume keywords.**

---

## 🌐 Live Production Links

| Service | Stack | Live URL |
|---|---|---|
| **React Frontend** | Firebase Hosting | 🔗 **[https://virehire-cdd94.web.app](https://virehire-cdd94.web.app)** |
| **Core API** | Java 21, Spring Boot 3 | 🔗 **[https://virehire-api-ty18.onrender.com](https://virehire-api-ty18.onrender.com)** |
| **AI Microservice** | Python 3.14, FastAPI | 🔗 **[https://virehire-python-ai-ty18.onrender.com](https://virehire-python-ai-ty18.onrender.com)** |
| **Database** | Google Firebase Firestore | 📦 `virehire-cdd94` |

---

## 🏗️ Architecture Overview

The platform uses a modern microservices architecture and a **Bring Your Own Keys (BYOK)** model for complete data privacy and cost control.

1. **Frontend (React SPA)**
   - Premium, interactive architecture showcase landing page.
   - Built with React 19, Vite, Tailwind CSS, and Framer Motion.
   - Deployed on **Firebase Hosting**.
   - Recruiter dashboard for configuring API keys, uploading candidate CSVs, and viewing detailed ranking reports.
2. **Spring Boot API (Core Backend)**
   - Manages Authentication (JWT) and User account data persisted in **Google Cloud Firestore**.
   - Handles the **BYOK secure storage**: User-provided GitHub and Groq API keys are encrypted at rest using AES-256 and decrypted in memory only when triggering the AI pipeline.
3. **Python AI Microservice (Stateless Pipeline)**
   - Fast, stateless pipeline built with FastAPI.
   - **Layer 1 (Semantic Retrieval)**: Uses ChromaDB and `sentence-transformers` embeddings to match candidate resumes against job descriptions.
   - **Layer 2 (Evidence Verification)**: Mathematical scoring and consistency verification of developer profiles.
   - **Layer 3 (LLM Reasoning)**: Uses Groq (Llama 3) to generate the final HIRE / REVIEW / REJECT verdicts.
   - Persists ranked candidates to **Firestore** under document collections (`/jobs/{job_id}/candidates`).

---

## 🚀 Key Features

- 🎯 **3-Layer AI Pipeline**: RAG + Evidence Scoring + LLM Reasoning.
- 📱 **Google Firebase Firestore**: Serverless NoSQL document database replacing relational PostgreSQL.
- 🔐 **Bring Your Own Keys (BYOK)**: Recruiters supply their own Groq and GitHub keys via the UI, encrypted with AES-256.
- 🐳 **Dockerized**: Fully containerized for seamless deployment.
- 📊 **Real-time Dashboard**: Upload CSVs, track background pipeline progress, and drill down into developer portfolios.

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| **Frontend** | React 19, TypeScript, Vite, Tailwind, Framer Motion |
| **Core API** | Java 21, Spring Boot 3, Spring Security, Firebase Admin SDK |
| **AI Service** | Python 3.14, FastAPI, Firebase Admin SDK, ChromaDB, Groq |
| **Database** | Google Cloud Firestore NoSQL |
| **Deployment** | Firebase Hosting, Render Web Services (Docker) |

---

## 💻 Local Development

### 1. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Provide your **Firebase Service Account Key path** (`FIREBASE_CREDENTIALS_PATH`), a **JWT Secret** (min 32 chars), and an **AES Encryption Key** (32 chars).

### 2. Start Services
```bash
# Start Python AI Backend
cd backend
python -m uvicorn app.main:app --reload --port 8000

# Start Spring Boot Backend
cd springboot
./mvnw.cmd spring-boot:run

# Start React Frontend
cd frontend
npm run dev
```

---

## 📄 License
MIT License
