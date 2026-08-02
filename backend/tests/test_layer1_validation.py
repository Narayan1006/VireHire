"""
Layer 1 Component Validation Test

Full pipeline: CSV -> CandidateInput -> ParsedResume -> TextChunker -> Embedder

Validates:
  1. CSV loading (>=5 candidates)
  2. Resume parsing
  3. Chunk generation (3-5 per candidate)
  4. Embedding generation (384 dims each)
  5. Processing time measurement
"""

import time
import sys

from app.parsers.csv_parser import load_csv
from app.parsers.resume_parser import ResumeParser
from app.embeddings.chunker import TextChunker, _estimate_tokens
from app.embeddings.embedder import Embedder, EMBEDDING_DIMENSION
from app.utils.logger import setup_logging

setup_logging(level="INFO", json_format=False)

CSV_PATH = "data/test_candidates.csv"
MIN_CANDIDATES = 5
failures = []


def fail(msg):
    failures.append(msg)
    print(f"  FAIL: {msg}")


def ok(msg):
    print(f"  PASS: {msg}")


# ── Step 1: Load CSV ──────────────────────────────────────────────
print("=" * 72)
print("STEP 1: CSV Loading")
print("=" * 72)
t0 = time.time()
candidates, total_rows = load_csv(CSV_PATH)
t_csv = time.time() - t0

print(f"  Loaded {len(candidates)} candidates from {total_rows} rows in {t_csv:.3f}s")

if len(candidates) >= MIN_CANDIDATES:
    ok(f"Candidate count >= {MIN_CANDIDATES}")
else:
    fail(f"Only {len(candidates)} candidates (need >= {MIN_CANDIDATES})")

# ── Step 2: Parse Resumes ─────────────────────────────────────────
print()
print("=" * 72)
print("STEP 2: Resume Parsing")
print("=" * 72)
parser = ResumeParser()
parsed_resumes = []
t0 = time.time()
for c in candidates:
    parsed = parser.parse_candidate(c)
    parsed_resumes.append(parsed)
t_parse = time.time() - t0

print(f"  Parsed {len(parsed_resumes)} resumes in {t_parse:.3f}s")
for p in parsed_resumes:
    print(f"    {p.name}: {len(p.skills)} skills, {len(p.timeline)} timeline entries, {len(p.text)} chars text")
ok("All candidates parsed")

# ── Step 3: Generate Chunks ───────────────────────────────────────
print()
print("=" * 72)
print("STEP 3: Chunk Generation")
print("=" * 72)
chunker = TextChunker()
all_chunks = {}
t0 = time.time()
for parsed in parsed_resumes:
    chunks = chunker.chunk_resume(parsed)
    all_chunks[parsed.candidate_id] = chunks
t_chunk = time.time() - t0

total_chunks = sum(len(c) for c in all_chunks.values())
print(f"  Generated {total_chunks} total chunks in {t_chunk:.3f}s")

for cid, chunks in all_chunks.items():
    name = next(p.name for p in parsed_resumes if p.candidate_id == cid)
    count = len(chunks)
    types = [c.chunk_type for c in chunks]
    indices = [c.chunk_index for c in chunks]

    if 3 <= count <= 5:
        ok(f"{name}: {count} chunks {types}")
    else:
        fail(f"{name}: {count} chunks (must be 3-5)")

    if indices != list(range(count)):
        fail(f"{name}: non-sequential indices {indices}")

# ── Step 4: Generate Embeddings ───────────────────────────────────
print()
print("=" * 72)
print("STEP 4: Embedding Generation")
print("=" * 72)
embedder = Embedder(model_name="all-MiniLM-L6-v2")

all_embeddings = {}
t0 = time.time()
for cid, chunks in all_chunks.items():
    texts = [c.text for c in chunks]
    embeddings = embedder.embed_batch(texts)
    all_embeddings[cid] = embeddings
t_embed = time.time() - t0

total_embeddings = sum(len(e) for e in all_embeddings.values())
print(f"  Generated {total_embeddings} embeddings in {t_embed:.3f}s")

# ── Step 5: Dimension Validation ──────────────────────────────────
print()
print("=" * 72)
print("STEP 5: Dimension Validation (every embedding must be 384-dim)")
print("=" * 72)
dim_errors = 0
for cid, embeddings in all_embeddings.items():
    for i, emb in enumerate(embeddings):
        if len(emb) != EMBEDDING_DIMENSION:
            fail(f"Candidate {cid}, chunk {i}: dim={len(emb)} (expected {EMBEDDING_DIMENSION})")
            dim_errors += 1

if dim_errors == 0:
    ok(f"All {total_embeddings} embeddings are {EMBEDDING_DIMENSION}-dimensional")
else:
    fail(f"{dim_errors} dimension mismatches found")

# ── Step 6: Per-Candidate Summary Table ───────────────────────────
print()
print("=" * 72)
print("STEP 6: Per-Candidate Summary")
print("=" * 72)
print()
print(f"  {'Name':<22} {'Chunks':>6} {'Embeddings':>10} {'Dim':>5} {'Status':>8}")
print(f"  {'-'*22} {'-'*6} {'-'*10} {'-'*5} {'-'*8}")

for parsed in parsed_resumes:
    cid = parsed.candidate_id
    chunks = all_chunks[cid]
    embeddings = all_embeddings[cid]
    chunk_count = len(chunks)
    embed_count = len(embeddings)
    dims = set(len(e) for e in embeddings)
    dim_str = str(dims.pop()) if len(dims) == 1 else str(dims)

    status = "OK"
    if not (3 <= chunk_count <= 5):
        status = "FAIL"
    if embed_count != chunk_count:
        status = "FAIL"
    if dims != {EMBEDDING_DIMENSION} and len(dims) != 0:
        status = "FAIL"

    print(f"  {parsed.name:<22} {chunk_count:>6} {embed_count:>10} {dim_str:>5} {status:>8}")

# ── Step 7: Timing Summary ────────────────────────────────────────
print()
print("=" * 72)
print("STEP 7: Timing Summary")
print("=" * 72)
t_total = t_csv + t_parse + t_chunk + t_embed
print(f"  CSV loading:     {t_csv:>8.3f}s")
print(f"  Resume parsing:  {t_parse:>8.3f}s")
print(f"  Chunk generation:{t_chunk:>8.3f}s")
print(f"  Embedding gen:   {t_embed:>8.3f}s")
print(f"  -------------------------")
print(f"  Total:           {t_total:>8.3f}s")
print(f"  Per candidate:   {t_total/len(candidates):>8.3f}s")

# ── Final Verdict ─────────────────────────────────────────────────
print()
print("=" * 72)
if failures:
    print(f"VALIDATION FAILED -- {len(failures)} failure(s):")
    for f in failures:
        print(f"  X {f}")
    sys.exit(1)
else:
    print("VALIDATION PASSED -- All Layer 1 components verified.")
    print(f"  {len(candidates)} candidates -> {total_chunks} chunks -> {total_embeddings} embeddings (384-dim)")
print("=" * 72)
