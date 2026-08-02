"""
VireHire AI - JSON to PostgreSQL Migration Script

Migrates existing candidate data from candidates.json to Supabase PostgreSQL.

Usage:
    python database/migrate_json_to_pg.py

Requirements:
    - Supabase tables created (run schema.sql first)
    - SUPABASE_URL and SUPABASE_ANON_KEY in .env
    - User must be logged in (provide user_id)
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

DATA_FILE = Path(__file__).parent.parent / "data" / "candidates.json"


def migrate_json_to_postgres(user_id: str):
    """
    Migrate candidates.json to PostgreSQL.
    
    Args:
        user_id: UUID of the user to assign jobs to
    """
    # Load settings
    settings = get_settings()
    
    if not settings.supabase_url or not settings.supabase_anon_key:
        logger.error("Supabase credentials not configured")
        return False
    
    # Create Supabase client
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    
    # Load JSON data
    if not DATA_FILE.exists():
        logger.warning("No candidates.json file found - nothing to migrate")
        return True
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error("Failed to load candidates.json: %s", e)
        return False
    
    jobs = data.get("jobs", [])
    if not jobs:
        logger.info("No jobs found in candidates.json")
        return True
    
    logger.info("Found %d jobs to migrate", len(jobs))
    
    # Migrate each job
    migrated_jobs = 0
    migrated_candidates = 0
    
    for job in jobs:
        job_id = job.get("job_id")
        job_description = job.get("job_description", "")
        timestamp = job.get("timestamp")
        candidates = job.get("candidates", [])
        
        if not job_id:
            logger.warning("Skipping job with no job_id")
            continue
        
        try:
            # 1. Insert job
            job_data = {
                "job_id": job_id,
                "user_id": user_id,
                "job_description": job_description,
            }
            
            # If timestamp exists, use it
            if timestamp:
                job_data["created_at"] = timestamp
                job_data["updated_at"] = timestamp
            
            client.table("jobs").upsert(job_data, on_conflict="job_id").execute()
            migrated_jobs += 1
            logger.info("Migrated job: %s (%d candidates)", job_id, len(candidates))
            
            # 2. Insert candidates
            if candidates:
                candidate_rows = []
                for c in candidates:
                    row = {
                        "job_id": job_id,
                        "candidate_id": c["id"],
                        "name": c["name"],
                        "email": c["email"],
                        "role": c["role"],
                        "rank": c["rank"],
                        "percentile": c["percentile"],
                        "pr_score": c["pr_score"],
                        "github_score": c["github_score"],
                        "dsa_score": c["dsa_score"],
                        "verdict": c["verdict"],
                        "skills": c["skills"],
                        "github_evidence": c["github_evidence"],
                        "leetcode": c["leetcode"],
                        "codeforces": c.get("codeforces"),
                        "timeline": c["timeline"],
                        "risk_flags": c["risk_flags"],
                        "summary": c["summary"],
                        "layer1_score": c["layer1_score"],
                        "layer2_score": c["layer2_score"],
                        "layer3_confidence": c["layer3_confidence"],
                    }
                    candidate_rows.append(row)
                
                client.table("candidates").insert(candidate_rows).execute()
                migrated_candidates += len(candidate_rows)
        
        except Exception as e:
            logger.error("Failed to migrate job %s: %s", job_id, e)
            continue
    
    logger.info(
        "Migration complete: %d jobs, %d candidates",
        migrated_jobs,
        migrated_candidates,
    )
    return True


def main():
    """Main migration entry point."""
    print("=" * 70)
    print("VireHire AI - JSON to PostgreSQL Migration")
    print("=" * 70)
    print()
    
    # Get user ID
    print("This script will migrate candidates.json to Supabase PostgreSQL.")
    print("All jobs will be assigned to a single user.")
    print()
    user_id = input("Enter your Supabase user ID (UUID): ").strip()
    
    if not user_id:
        print("Error: User ID is required")
        return
    
    # Validate UUID format (basic check)
    if len(user_id) != 36 or user_id.count("-") != 4:
        print("Error: Invalid UUID format")
        print("Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        return
    
    print()
    print(f"Migrating to user: {user_id}")
    print()
    
    # Confirm
    confirm = input("Continue? (yes/no): ").strip().lower()
    if confirm not in ["yes", "y"]:
        print("Migration cancelled")
        return
    
    print()
    print("Starting migration...")
    print()
    
    # Run migration
    success = migrate_json_to_postgres(user_id)
    
    print()
    if success:
        print("✅ Migration completed successfully!")
        print()
        print("Next steps:")
        print("1. Verify data in Supabase Table Editor")
        print("2. Update backend to use PostgreSQL store")
        print("3. Backup candidates.json (optional)")
        print("4. Remove candidates.json from git (add to .gitignore)")
    else:
        print("❌ Migration failed - check logs for details")


if __name__ == "__main__":
    main()
