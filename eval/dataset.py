"""
VeriHire v2 - Evaluation Dataset (Milestone 4)
Synthetic, consented dataset of realistic job queries and diverse candidate profiles
with ground-truth relevance grades (0 to 3) for reproducible benchmarking.

Ground Truth Relevance Scale:
- Grade 3: Highly relevant expert with strong matching skills and verified public proof of work.
- Grade 2: Solid relevant match with matching skills and moderate evidence.
- Grade 1: Superficial / keyword match (mentions terms but lacks verified proof).
- Grade 0: Irrelevant / non-technical or mismatched specialty.
"""

from typing import Any, Dict, List

EVAL_QUERIES = [
    {
        "id": "query_backend_python",
        "title": "Senior Python Backend Engineer",
        "description": (
            "We are looking for a Senior Python Backend Engineer to build high-concurrency microservices. "
            "Required skills: Python 3.12, FastAPI, PostgreSQL, AsyncIO, Docker, distributed systems, "
            "and database optimization. Experience with open source contributions, high test coverage, "
            "and API performance tuning is strongly desired."
        ),
    },
    {
        "id": "query_frontend_react",
        "title": "Senior Frontend Engineer (React & TypeScript)",
        "description": (
            "Looking for an experienced Frontend Engineer specialized in modern React, TypeScript, "
            "and Tailwind CSS. Must have deep experience with component design systems, state management, "
            "client-side performance optimization, accessible UI (WCAG), and Vite/Next.js tooling."
        ),
    },
    {
        "id": "query_devops_cloud",
        "title": "Cloud Infrastructure & DevOps Engineer",
        "description": (
            "Seeking a DevOps/SRE Engineer to manage containerized infrastructure and automated CI/CD. "
            "Required: Kubernetes, Docker, Terraform, AWS/GCP, Prometheus monitoring, Linux systems administration, "
            "and zero-downtime deployment pipelines."
        ),
    },
]

# 30 Diverse synthetic candidates covering expert, solid, superficial, and irrelevant profiles
CANDIDATE_POOL: List[Dict[str, Any]] = [
    # --- Python Backend Candidates ---
    {
        "id": "cand_py_expert_1",
        "name": "Marcus Vance",
        "resume_text": (
            "Senior Backend Engineer with 8 years of experience building high-throughput microservices in Python, "
            "FastAPI, and PostgreSQL. Built async event-driven systems handling 50k req/sec with AsyncIO and Redis. "
            "Expert in PostgreSQL schema design, indexing, and query optimization. Strong CI/CD and Docker workflow."
        ),
        "evidence": [
            {
                "source": "github",
                "status": "verified",
                "username": "marcusv-dev",
                "payload": {
                    "total_stars": 380,
                    "merged_external_prs": 18,
                    "commit_contributions": 1200,
                    "public_repos_count": 28,
                    "languages_histogram": {"Python": 450000, "SQL": 80000, "Docker": 20000},
                },
            },
            {
                "source": "leetcode",
                "status": "verified",
                "username": "marcusv_algo",
                "payload": {
                    "total_solved": 420,
                    "easy_solved": 120,
                    "medium_solved": 220,
                    "hard_solved": 80,
                    "contest_rating": 2150,
                },
            },
        ],
        "relevance": {"query_backend_python": 3, "query_frontend_react": 0, "query_devops_cloud": 1},
    },
    {
        "id": "cand_py_solid_2",
        "name": "Elena Rostova",
        "resume_text": (
            "Backend Developer with 4 years specializing in Python, Django, and FastAPI. "
            "Maintains RESTful APIs backed by PostgreSQL and Celery task queues. "
            "Dockerized local environments and wrote automated PyTest suites with 90% coverage."
        ),
        "evidence": [
            {
                "source": "github",
                "status": "verified",
                "username": "elena-rostova",
                "payload": {
                    "total_stars": 85,
                    "merged_external_prs": 5,
                    "commit_contributions": 650,
                    "public_repos_count": 14,
                    "languages_histogram": {"Python": 220000, "PostgreSQL": 40000},
                },
            },
            {
                "source": "leetcode",
                "status": "verified",
                "username": "elena_r",
                "payload": {
                    "total_solved": 190,
                    "easy_solved": 80,
                    "medium_solved": 95,
                    "hard_solved": 15,
                    "contest_rating": 1650,
                },
            },
        ],
        "relevance": {"query_backend_python": 2, "query_frontend_react": 0, "query_devops_cloud": 1},
    },
    {
        "id": "cand_py_keyword_3",
        "name": "Brian Keyword",
        "resume_text": (
            "Software engineer with familiarity in Python, FastAPI, PostgreSQL, Docker, and distributed systems. "
            "Attended workshops on microservices and cloud databases. Enthusiastic learner seeking new opportunities."
        ),
        "evidence": [
            {
                "source": "github",
                "status": "unverified",
                "username": "briankeyword",
                "reason": "not_found",
                "payload": {},
            }
        ],
        "relevance": {"query_backend_python": 1, "query_frontend_react": 0, "query_devops_cloud": 0},
    },
    {
        "id": "cand_py_expert_4",
        "name": "Tariq Al-Mansoor",
        "resume_text": (
            "Principal Systems Architect with extensive background in Python, AsyncIO, distributed database engines, "
            "and high-performance FastAPI backends. Authored popular open source async libraries with thousands of stars. "
            "Deep experience with PostgreSQL replication, connection pooling, and Docker container orchestration."
        ),
        "evidence": [
            {
                "source": "github",
                "status": "verified",
                "username": "tariq-mansoor",
                "payload": {
                    "total_stars": 820,
                    "merged_external_prs": 26,
                    "commit_contributions": 1450,
                    "public_repos_count": 35,
                    "languages_histogram": {"Python": 750000, "C++": 120000, "PostgreSQL": 90000},
                },
            }
        ],
        "relevance": {"query_backend_python": 3, "query_frontend_react": 0, "query_devops_cloud": 2},
    },

    # --- Frontend React & TypeScript Candidates ---
    {
        "id": "cand_fe_expert_1",
        "name": "Chloe Lin",
        "resume_text": (
            "Lead Frontend Architect with 7 years of specialized experience in React, TypeScript, Next.js, and Tailwind CSS. "
            "Designed and built enterprise design systems adopted by over 200 developers. "
            "Deep expertise in React 19 concurrent features, web performance budgets (Core Web Vitals), and accessibility (ARIA)."
        ),
        "evidence": [
            {
                "source": "github",
                "status": "verified",
                "username": "chloelin-ui",
                "payload": {
                    "total_stars": 490,
                    "merged_external_prs": 22,
                    "commit_contributions": 1380,
                    "public_repos_count": 24,
                    "languages_histogram": {"TypeScript": 600000, "CSS": 90000, "JavaScript": 150000},
                },
            }
        ],
        "relevance": {"query_backend_python": 0, "query_frontend_react": 3, "query_devops_cloud": 0},
    },
    {
        "id": "cand_fe_solid_2",
        "name": "David Miller",
        "resume_text": (
            "Frontend Developer with 3.5 years of experience creating responsive web apps using React, TypeScript, "
            "and Tailwind CSS. Integrated REST and GraphQL APIs, optimized render lifecycles with Zustand state management."
        ),
        "evidence": [
            {
                "source": "github",
                "status": "verified",
                "username": "david-miller-fe",
                "payload": {
                    "total_stars": 60,
                    "merged_external_prs": 4,
                    "commit_contributions": 520,
                    "public_repos_count": 12,
                    "languages_histogram": {"TypeScript": 180000, "HTML": 30000},
                },
            }
        ],
        "relevance": {"query_backend_python": 0, "query_frontend_react": 2, "query_devops_cloud": 0},
    },
    {
        "id": "cand_fe_keyword_3",
        "name": "Fiona Buzzword",
        "resume_text": (
            "Junior developer resume listing React, TypeScript, Tailwind, Next.js, state management, and web performance. "
            "Completed frontend coding bootcamp exercises and personal portfolio site."
        ),
        "evidence": [
            {
                "source": "github",
                "status": "unverified",
                "username": "fiona-buzz",
                "reason": "no_proof",
                "payload": {},
            }
        ],
        "relevance": {"query_backend_python": 0, "query_frontend_react": 1, "query_devops_cloud": 0},
    },

    # --- DevOps & Cloud Infrastructure Candidates ---
    {
        "id": "cand_devops_expert_1",
        "name": "Siddharth Rao",
        "resume_text": (
            "Staff Infrastructure / DevOps Engineer with 9 years of experience architecting multi-region Kubernetes "
            "clusters and Infrastructure as Code using Terraform. Built zero-downtime deployment pipelines for 60+ microservices "
            "on AWS and GCP. Deep knowledge of Prometheus, Grafana, Docker, Helm, and Linux kernel networking."
        ),
        "evidence": [
            {
                "source": "github",
                "status": "verified",
                "username": "siddharth-infra",
                "payload": {
                    "total_stars": 310,
                    "merged_external_prs": 14,
                    "commit_contributions": 980,
                    "public_repos_count": 22,
                    "languages_histogram": {"HCL": 250000, "Go": 320000, "Shell": 80000, "Python": 110000},
                },
            }
        ],
        "relevance": {"query_backend_python": 1, "query_frontend_react": 0, "query_devops_cloud": 3},
    },
    {
        "id": "cand_devops_solid_2",
        "name": "Kelsey Adams",
        "resume_text": (
            "DevOps Engineer with 4 years deploying containerized apps with Docker and Kubernetes on AWS. "
            "Wrote Terraform modules for VPC, RDS, and EKS. Configured GitHub Actions CI/CD and Prometheus alerts."
        ),
        "evidence": [
            {
                "source": "github",
                "status": "verified",
                "username": "kelsey-cloud",
                "payload": {
                    "total_stars": 45,
                    "merged_external_prs": 3,
                    "commit_contributions": 410,
                    "public_repos_count": 9,
                    "languages_histogram": {"HCL": 90000, "Shell": 60000},
                },
            }
        ],
        "relevance": {"query_backend_python": 0, "query_frontend_react": 0, "query_devops_cloud": 2},
    },

    # --- Irrelevant / Off-domain Candidates ---
    {
        "id": "cand_irrelevant_1",
        "name": "Arthur Pendelton",
        "resume_text": (
            "Executive Chef and Restaurant Manager with 12 years directing culinary staff, inventory management, "
            "food safety compliance, menu design, vendor negotiations, and kitchen operations."
        ),
        "evidence": [],
        "relevance": {"query_backend_python": 0, "query_frontend_react": 0, "query_devops_cloud": 0},
    },
    {
        "id": "cand_irrelevant_2",
        "name": "Grace Hopperly",
        "resume_text": (
            "Commercial Real Estate Broker specialized in industrial lease transactions, tenant representation, "
            "market valuation, and property contract negotiations across regional territories."
        ),
        "evidence": [],
        "relevance": {"query_backend_python": 0, "query_frontend_react": 0, "query_devops_cloud": 0},
    },
    {
        "id": "cand_irrelevant_3",
        "name": "Oliver Twist",
        "resume_text": (
            "Digital Marketing Specialist with experience in SEO content strategy, Google Ad campaigns, "
            "copywriting, social media community engagement, and lead generation analytics."
        ),
        "evidence": [],
        "relevance": {"query_backend_python": 0, "query_frontend_react": 0, "query_devops_cloud": 0},
    },
]
