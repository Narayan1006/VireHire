"""
Technology vocabulary with aliases for skill overlap computation.
Defines ~80 canonical technologies across programming languages,
frameworks, databases, cloud/devops, and data/ML stacks.
"""

from typing import Dict, List, Set
import re

# Mapping of Canonical Technology Name -> list of aliases / variants
TECH_VOCABULARY: Dict[str, List[str]] = {
    # Languages
    "Python": ["python", "py"],
    "JavaScript": ["javascript", "js", "ecmascript"],
    "TypeScript": ["typescript", "ts"],
    "Java": ["java"],
    "C++": ["c++", "cpp"],
    "C#": ["c#", "csharp", ".net", "dotnet"],
    "Go": ["golang", "go"],
    "Rust": ["rust"],
    "Ruby": ["ruby"],
    "PHP": ["php"],
    "Swift": ["swift"],
    "Kotlin": ["kotlin"],
    "Scala": ["scala"],
    "R": ["rstats", "r language"],
    "Dart": ["dart"],
    "Shell": ["bash", "shell", "zsh"],
    "SQL": ["sql"],
    "HTML": ["html", "html5"],
    "CSS": ["css", "css3"],
    "Sass": ["sass", "scss"],
    # Frontend & Fullstack Frameworks
    "React": ["react", "reactjs", "react.js"],
    "Vue": ["vue", "vuejs", "vue.js"],
    "Angular": ["angular", "angularjs"],
    "Svelte": ["svelte"],
    "Next.js": ["nextjs", "next.js"],
    "Tailwind CSS": ["tailwind", "tailwindcss"],
    "Bootstrap": ["bootstrap"],
    # Backend Frameworks & Runtimes
    "Node.js": ["nodejs", "node.js", "node"],
    "Express": ["express", "expressjs"],
    "FastAPI": ["fastapi"],
    "Django": ["django"],
    "Flask": ["flask"],
    "Spring Boot": ["spring boot", "springboot", "spring framework"],
    "Ruby on Rails": ["rails", "ruby on rails"],
    "ASP.NET": ["asp.net", "aspnet"],
    "GraphQL": ["graphql"],
    "gRPC": ["grpc"],
    "REST": ["rest api", "restful", "rest apis"],
    # Databases & Caching
    "PostgreSQL": ["postgres", "postgresql", "psql"],
    "MySQL": ["mysql"],
    "SQLite": ["sqlite"],
    "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis"],
    "Elasticsearch": ["elasticsearch", "opensearch"],
    "Cassandra": ["cassandra"],
    "DynamoDB": ["dynamodb"],
    "Firebase": ["firebase", "firestore"],
    "Supabase": ["supabase"],
    "Snowflake": ["snowflake"],
    "BigQuery": ["bigquery"],
    # Cloud, DevOps & Infrastructure
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Terraform": ["terraform"],
    "Ansible": ["ansible"],
    "AWS": ["aws", "amazon web services", "ec2", "s3", "lambda"],
    "GCP": ["gcp", "google cloud", "google cloud platform"],
    "Azure": ["azure", "microsoft azure"],
    "Linux": ["linux", "ubuntu", "debian", "centos", "redhat"],
    "Git": ["git", "github", "gitlab"],
    "CI/CD": ["ci/cd", "cicd", "github actions", "gitlab ci", "jenkins"],
    "Nginx": ["nginx"],
    "Kafka": ["kafka", "apache kafka"],
    "RabbitMQ": ["rabbitmq"],
    "Airflow": ["airflow", "apache airflow"],
    "Celery": ["celery"],
    # Data & Machine Learning / AI
    "PyTorch": ["pytorch"],
    "TensorFlow": ["tensorflow", "keras"],
    "Scikit-learn": ["scikit-learn", "sklearn"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "Apache Spark": ["spark", "pyspark", "apache spark"],
    "Hadoop": ["hadoop"],
    "LangChain": ["langchain"],
    "LlamaIndex": ["llamaindex"],
    "Hugging Face": ["huggingface", "transformers"],
    "OpenCV": ["opencv"],
    # Observability & Testing
    "Prometheus": ["prometheus"],
    "Grafana": ["grafana"],
    "Pytest": ["pytest"],
    "Jest": ["jest"],
    "Playwright": ["playwright"],
    "Cypress": ["cypress"],
}


def _compile_patterns() -> Dict[str, List[re.Pattern]]:
    compiled: Dict[str, List[re.Pattern]] = {}
    for canon, aliases in TECH_VOCABULARY.items():
        patterns = []
        for alias in aliases:
            # Word boundary matching that accommodates symbols like ++ or . or #
            escaped = re.escape(alias)
            # If alias starts/ends with alphanumeric, require \b; otherwise require non-word or string bounds
            prefix = r"\b" if re.match(r"^\w", alias) else r"(?:^|\W)"
            suffix = r"\b" if re.search(r"\w$", alias) else r"(?:$|\W)"
            pattern = re.compile(rf"{prefix}{escaped}{suffix}", re.IGNORECASE)
            patterns.append(pattern)
        compiled[canon] = patterns
    return compiled


_COMPILED_PATTERNS = _compile_patterns()


def extract_technologies(text: str) -> Set[str]:
    """
    Extracts canonical technology names from any text (e.g. job description,
    repo name, readme snippet, or candidate profile).
    """
    if not text:
        return set()

    found = set()
    for canon, patterns in _COMPILED_PATTERNS.items():
        for pat in patterns:
            if pat.search(text):
                found.add(canon)
                break
    return found
