FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for chromadb and numpy
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spacy language model
RUN python -m spacy download en_core_web_sm

COPY . .

# ChromaDB persistence directory
RUN mkdir -p data/chroma_db

EXPOSE 8000

# Stateless AI service — no DB writes, no uploads directory needed
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
