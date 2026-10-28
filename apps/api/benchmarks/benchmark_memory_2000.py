"""
VeriHire v2 - Full Pipeline Benchmark (2,000 Candidates + Hybrid Retrieval)
Measures peak memory (RSS), embedding time, and retrieval time.
Render free instance limit: 512 MB.
"""

import os
import random
import threading
import time
import uuid
import psutil
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base, Candidate, Job, Ranking, User
from app.services.embedding import compute_embeddings
from app.services.retrieval import hybrid_retrieval

# Continuous memory monitor
peak_rss_mb = 0.0
stop_monitor = False


def monitor_memory():
    global peak_rss_mb
    proc = psutil.Process(os.getpid())
    while not stop_monitor:
        rss = proc.memory_info().rss / (1024 * 1024)
        if rss > peak_rss_mb:
            peak_rss_mb = rss
        time.sleep(0.05)


def run_benchmark():
    global stop_monitor, peak_rss_mb
    db_url = (
        os.getenv("BENCHMARK_DATABASE_URL")
        or os.getenv("TEST_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or "postgresql+psycopg://postgres:password@localhost:5433/verihire"
    )

    if "supabase" in db_url.lower():
        raise RuntimeError("CRITICAL: Benchmark refused to run against Supabase database!")

    print(f"Connecting to database (host: {db_url.split('@')[-1].split('/')[0]})...")

    engine = create_engine(db_url, pool_pre_ping=True)
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    proc = psutil.Process(os.getpid())
    base_rss = proc.memory_info().rss / (1024 * 1024)
    peak_rss_mb = base_rss
    print(f"Base RSS memory: {base_rss:.2f} MB")

    # Start memory monitoring thread
    monitor_thread = threading.Thread(target=monitor_memory, daemon=True)
    monitor_thread.start()

    session = Session(engine)
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()

    try:
        user = User(
            id=user_id,
            email=f"bench_{user_id.hex[:8]}@example.com",
            password_hash="bench_hash",
        )
        job = Job(
            id=job_id,
            owner_id=user_id,
            title="Senior Distributed Systems & Backend Engineer",
            description=(
                "We are seeking an experienced Backend Engineer proficient in Python, FastAPI, Docker, and PostgreSQL. "
                "The role requires building scalable distributed systems, RESTful APIs, vector search pipelines, and microservices architecture. "
                "Strong knowledge of async programming, database optimization, and high availability systems is essential."
            ),
            status="draft",
        )
        session.add(user)
        session.add(job)
        session.commit()

        # 1. Generate 2,000 synthetic candidates
        print("Generating 2,000 synthetic candidates...")
        random.seed(42)
        skills = [
            "Python", "FastAPI", "Docker", "PostgreSQL", "Kubernetes", "AWS", "Redis",
            "Distributed Systems", "GraphQL", "Microservices", "Machine Learning",
            "React", "TypeScript", "Node.js", "Java", "Go", "Elasticsearch", "CI/CD"
        ]
        candidates = []
        for i in range(2000):
            cand_skills = random.sample(skills, 5)
            cand_text = (
                f"Candidate {i} Resume.\n"
                f"Experienced software engineer specializing in {', '.join(cand_skills)}. "
                f"Developed high performance backend services and scalable database architectures. "
                f"Demonstrated track record of delivering resilient cloud-native applications with CI/CD and automated testing. "
                f"Experience: Senior Software Engineer at Tech Corp {i}. Led migration of monolithic services to microservices."
            )
            cand = Candidate(
                id=uuid.uuid4(),
                job_id=job_id,
                name=f"Candidate {i}",
                email=f"cand_{i}_{uuid.uuid4().hex[:6]}@example.com",
                resume_text=cand_text,
            )
            candidates.append(cand)

        session.add_all(candidates)
        session.commit()
        print("2,000 candidates saved to database.")

        # 2. Embedding phase (batch size 16 to stay below 450 MB target)
        batch_size = 16
        print(f"Embedding 2,000 candidate resumes in batches of {batch_size}...")
        all_texts = [c.resume_text for c in candidates]
        start_embed = time.perf_counter()
        embeddings = compute_embeddings(all_texts, batch_size=batch_size)
        for cand, emb in zip(candidates, embeddings):
            cand.embedding = emb
        session.commit()
        embed_time = time.perf_counter() - start_embed
        print(f"Embedding completed in {embed_time:.2f} seconds ({len(embeddings)} vectors, batch_size={batch_size}).")

        # 3. Hybrid retrieval phase (K=200)
        print("Running hybrid retrieval (K=200)...")
        start_retrieval = time.perf_counter()
        rankings = hybrid_retrieval(
            job_id=job_id,
            query_text=job.description,
            db=session,
            top_k=200,
        )
        retrieval_time = time.perf_counter() - start_retrieval
        print(f"Retrieval completed in {retrieval_time:.4f} seconds ({len(rankings)} rankings returned).")

    finally:
        # Cleanup benchmark data
        print("Cleaning up benchmark records...")
        try:
            session.query(Ranking).filter(Ranking.job_id == job_id).delete()
            session.query(Candidate).filter(Candidate.job_id == job_id).delete()
            session.query(Job).filter(Job.id == job_id).delete()
            session.query(User).filter(User.id == user_id).delete()
            session.commit()
        except Exception as e:
            print(f"Cleanup warning: {e}")
        session.close()

        stop_monitor = True
        monitor_thread.join(timeout=1.0)

    print("\n" + "=" * 50)
    print("BENCHMARK RESULTS")
    print("=" * 50)
    print("Candidates Ingested: 2,000")
    print(f"Embedding Batch Size: {batch_size}")
    print(f"Embedding Time:      {embed_time:.2f} s ({embed_time / 2000 * 1000:.1f} ms/candidate)")
    print(f"Retrieval Time:      {retrieval_time:.4f} s ({retrieval_time * 1000:.1f} ms)")
    print(f"Base RSS Memory:     {base_rss:.2f} MB")
    print(f"Peak RSS Memory:     {peak_rss_mb:.2f} MB")
    print(f"Memory Overhead:     {peak_rss_mb - base_rss:.2f} MB")
    print(f"Render 512MB Limit:  {'SURVIVED' if peak_rss_mb < 512 else 'FAILED'}")
    print(f"450MB Target:        {'MET' if peak_rss_mb <= 450 else 'EXCEEDED'}")
    print("=" * 50 + "\n")

    assert len(embeddings) == 2000
    assert len(rankings) == 200
    assert peak_rss_mb < 512, f"Peak memory {peak_rss_mb:.2f} MB exceeded 512 MB limit!"


if __name__ == "__main__":
    run_benchmark()
