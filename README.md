# VeriHire AI

**Evidence-backed hiring intelligence — rank candidates by proven GitHub and LeetCode signals, not resume keywords.**

![VeriHire AI Architecture](docs/architecture.png) *(Note: Replace with actual image if available)*

VeriHire AI is a microservices-based platform built for technical recruiters and engineering teams. It evaluates candidates by running a **3-Layer AI Pipeline** that extracts semantic meaning from resumes, cross-references claims against live developer platforms (GitHub, LeetCode), and generates detailed, reasoning-backed verdicts using LLMs.

---

## 🏗️ Architecture Overview

The platform uses a modern microservices architecture and a **Bring Your Own Keys (BYOK)** model for complete data privacy and cost control.

1. **Frontend (React SPA)**
   - Premium, interactive architecture showcase landing page.
   - Built with React 19, Vite, Tailwind CSS, and Framer Motion.
   - Recruiter dashboard for configuring API keys, uploading candidate CSVs, and viewing detailed ranking reports.
2. **Spring Boot API (Core Backend)**
   - Manages Authentication (JWT), Job configurations, and Candidate data.
   - Handles the **BYOK secure storage**: User-provided GitHub and Groq API keys are encrypted at rest using AES-256 and decrypted in memory only when triggering the AI pipeline.
3. **Python AI Microservice (Stateless Pipeline)**
   - Fast, stateless pipeline built with FastAPI.
   - **Layer 1 (Semantic Retrieval)**: Uses ChromaDB and `sentence-transformers` to match resumes against job descriptions.
   - **Layer 2 (Evidence Verification)**: Fetches live data from GitHub APIs using the recruiter's injected token.
   - **Layer 3 (LLM Reasoning)**: Uses Groq (Llama 3) to generate the final HIRE / REVIEW / REJECT verdicts.

---

## 🚀 Key Features

- 🎯 **3-Layer AI Pipeline**: RAG + External API Evidence + LLM Reasoning.
- 🔐 **Bring Your Own Keys (BYOK)**: Recruiters supply their own Groq and GitHub keys via the UI. Keys are AES-256 encrypted in PostgreSQL.
- 🐳 **Dockerized**: Fully containerized with Docker Compose for seamless deployment.
- ⚡ **GPU Acceleration**: The Python service automatically detects CUDA for lightning-fast embedding generation.
- 📊 **Real-time Dashboard**: Upload CSVs, track background pipeline progress, and drill down into developer portfolios.

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| **Frontend** | React 19, TypeScript, Vite, Tailwind, Framer Motion |
| **Core API** | Java 21, Spring Boot 3, Spring Security, Hibernate |
| **AI Service** | Python 3.10+, FastAPI, ChromaDB, Groq, Pandas |
| **Database** | PostgreSQL (Supabase) |
| **Deployment** | Docker, Nginx, Render Web Services |

---

## 💻 Local Development (Docker Compose)

The easiest way to run the entire stack locally is using Docker Compose.

### 1. Configure Environments
Clone the repository and copy the environment template:
```bash
cp .env.example .env
```

Edit `.env` and provide your **Supabase PostgreSQL credentials**, a **JWT Secret** (min 32 chars), and an **AES Encryption Key** (exactly 32 chars).

*Note: You do NOT put your Groq or GitHub keys in the `.env` file. You will enter them in the Web UI later.*

### 2. Start the Stack
```bash
docker compose up --build -d
```
This spins up three containers:
- `frontend` (Nginx + React) on `http://localhost:80` (or `http://localhost:5173` if running dev server)
- `springboot` (API) on `http://localhost:8080`
- `python-ai` (Pipeline) on `http://localhost:8000`

### 3. Usage
1. Open your browser and navigate to the frontend.
2. Sign up for an account.
3. Navigate to **Settings** and enter your GitHub PAT and Groq API Key.
4. Go to the **Dashboard**, enter a Job Description, and upload a `candidates.csv` file.

---

## ☁️ Production Deployment (Render)

To deploy to a cloud provider like Render:

1. **Deploy Python AI Service**
   - Environment: Docker
   - Root Directory: `backend`
   - Env Vars: `CORS_ORIGINS=*`, `CHROMADB_PATH=/app/data/chroma_db`

2. **Deploy Spring Boot Service**
   - Environment: Docker
   - Root Directory: `springboot`
   - Env Vars: Include your Supabase credentials, `JWT_SECRET`, `APP_ENCRYPTION_KEY`, and set `AI_SERVICE_URL` to the URL of your deployed Python service.

3. **Deploy Frontend**
   - Build Command: `npm install && npm run build`
   - Publish Directory: `dist`
   - Env Vars: `VITE_API_BASE_URL` pointing to your Spring Boot service URL.

---

## 📄 License
MIT License
