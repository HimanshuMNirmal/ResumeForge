"""Skill taxonomy and classification helper.

Categorizes software engineering technologies, languages, frameworks, libraries,
and tools into canonical resume skill groups.
"""
from __future__ import annotations

import re

# Canonical categories
CATEGORY_LANGUAGES = "Languages"
CATEGORY_FRONTEND = "Frontend"
CATEGORY_MOBILE = "Mobile"
CATEGORY_BACKEND = "Backend & Architecture"
CATEGORY_DATABASES = "Databases"
CATEGORY_CLOUD_DEVOPS = "Cloud & DevOps"
CATEGORY_AI_DATA = "AI/ML & Data"
CATEGORY_BLOCKCHAIN = "Blockchain"
CATEGORY_TOOLS = "Tools"
CATEGORY_OTHER = "Other"

# Exact / normalized name mappings to categories
_KNOWN_SKILL_CATEGORIES: dict[str, str] = {
    # Languages
    "javascript": CATEGORY_LANGUAGES,
    "typescript": CATEGORY_LANGUAGES,
    "js": CATEGORY_LANGUAGES,
    "ts": CATEGORY_LANGUAGES,
    "python": CATEGORY_LANGUAGES,
    "py": CATEGORY_LANGUAGES,
    "java": CATEGORY_LANGUAGES,
    "c": CATEGORY_LANGUAGES,
    "c++": CATEGORY_LANGUAGES,
    "cpp": CATEGORY_LANGUAGES,
    "c#": CATEGORY_LANGUAGES,
    "csharp": CATEGORY_LANGUAGES,
    "dart": CATEGORY_LANGUAGES,
    "html": CATEGORY_LANGUAGES,
    "html5": CATEGORY_LANGUAGES,
    "css": CATEGORY_LANGUAGES,
    "css3": CATEGORY_LANGUAGES,
    "go": CATEGORY_LANGUAGES,
    "golang": CATEGORY_LANGUAGES,
    "rust": CATEGORY_LANGUAGES,
    "ruby": CATEGORY_LANGUAGES,
    "php": CATEGORY_LANGUAGES,
    "kotlin": CATEGORY_LANGUAGES,
    "swift": CATEGORY_LANGUAGES,
    "sql": CATEGORY_LANGUAGES,
    "bash": CATEGORY_LANGUAGES,
    "shell": CATEGORY_LANGUAGES,
    "r": CATEGORY_LANGUAGES,
    "scala": CATEGORY_LANGUAGES,

    # Frontend
    "react": CATEGORY_FRONTEND,
    "react.js": CATEGORY_FRONTEND,
    "reactjs": CATEGORY_FRONTEND,
    "next.js": CATEGORY_FRONTEND,
    "nextjs": CATEGORY_FRONTEND,
    "next": CATEGORY_FRONTEND,
    "redux": CATEGORY_FRONTEND,
    "redux toolkit": CATEGORY_FRONTEND,
    "vue": CATEGORY_FRONTEND,
    "vue.js": CATEGORY_FRONTEND,
    "vuejs": CATEGORY_FRONTEND,
    "angular": CATEGORY_FRONTEND,
    "angularjs": CATEGORY_FRONTEND,
    "svelte": CATEGORY_FRONTEND,
    "tailwind": CATEGORY_FRONTEND,
    "tailwind css": CATEGORY_FRONTEND,
    "tailwindcss": CATEGORY_FRONTEND,
    "bootstrap": CATEGORY_FRONTEND,
    "sass": CATEGORY_FRONTEND,
    "scss": CATEGORY_FRONTEND,
    "vite": CATEGORY_FRONTEND,
    "webpack": CATEGORY_FRONTEND,

    # Mobile
    "react native": CATEGORY_MOBILE,
    "reactnative": CATEGORY_MOBILE,
    "expo": CATEGORY_MOBILE,
    "expo cli": CATEGORY_MOBILE,
    "flutter": CATEGORY_MOBILE,
    "android": CATEGORY_MOBILE,
    "android (java)": CATEGORY_MOBILE,
    "ios": CATEGORY_MOBILE,
    "swiftui": CATEGORY_MOBILE,
    "jetpack compose": CATEGORY_MOBILE,

    # Backend & Architecture
    "node.js": CATEGORY_BACKEND,
    "nodejs": CATEGORY_BACKEND,
    "node": CATEGORY_BACKEND,
    "express.js": CATEGORY_BACKEND,
    "expressjs": CATEGORY_BACKEND,
    "express": CATEGORY_BACKEND,
    "rest apis": CATEGORY_BACKEND,
    "rest api": CATEGORY_BACKEND,
    "restful apis": CATEGORY_BACKEND,
    "restful api": CATEGORY_BACKEND,
    "rest": CATEGORY_BACKEND,
    "graphql": CATEGORY_BACKEND,
    "jwt authentication": CATEGORY_BACKEND,
    "jwt": CATEGORY_BACKEND,
    "jwt auth": CATEGORY_BACKEND,
    "role-based access control": CATEGORY_BACKEND,
    "rbac": CATEGORY_BACKEND,
    "role-based access": CATEGORY_BACKEND,
    "websockets": CATEGORY_BACKEND,
    "websocket": CATEGORY_BACKEND,
    "asp.net core": CATEGORY_BACKEND,
    "asp.net": CATEGORY_BACKEND,
    ".net core": CATEGORY_BACKEND,
    ".net": CATEGORY_BACKEND,
    "fastapi": CATEGORY_BACKEND,
    "microservices": CATEGORY_BACKEND,
    "clean architecture": CATEGORY_BACKEND,
    "firebase": CATEGORY_BACKEND,
    "etl pipelines": CATEGORY_BACKEND,
    "etl": CATEGORY_BACKEND,
    "nestjs": CATEGORY_BACKEND,
    "nest.js": CATEGORY_BACKEND,
    "oauth2": CATEGORY_BACKEND,
    "oauth": CATEGORY_BACKEND,
    "oauth 2.0": CATEGORY_BACKEND,
    "socket.io": CATEGORY_BACKEND,
    "socketio": CATEGORY_BACKEND,
    "django": CATEGORY_BACKEND,
    "flask": CATEGORY_BACKEND,
    "spring": CATEGORY_BACKEND,
    "spring boot": CATEGORY_BACKEND,
    "grpc": CATEGORY_BACKEND,
    "rabbitmq": CATEGORY_BACKEND,
    "kafka": CATEGORY_BACKEND,
    "apache kafka": CATEGORY_BACKEND,
    "celery": CATEGORY_BACKEND,

    # Databases
    "mongodb": CATEGORY_DATABASES,
    "mongo": CATEGORY_DATABASES,
    "postgresql": CATEGORY_DATABASES,
    "postgres": CATEGORY_DATABASES,
    "sqlalchemy": CATEGORY_DATABASES,
    "sqlite": CATEGORY_DATABASES,
    "mysql": CATEGORY_DATABASES,
    "prisma": CATEGORY_DATABASES,
    "prisma orm": CATEGORY_DATABASES,
    "row-level security": CATEGORY_DATABASES,
    "rls": CATEGORY_DATABASES,
    "postgresql rls": CATEGORY_DATABASES,
    "redis": CATEGORY_DATABASES,
    "cassandra": CATEGORY_DATABASES,
    "dynamodb": CATEGORY_DATABASES,
    "oracle": CATEGORY_DATABASES,
    "neo4j": CATEGORY_DATABASES,

    # AI/ML & Data
    "pandas": CATEGORY_AI_DATA,
    "numpy": CATEGORY_AI_DATA,
    "pytorch": CATEGORY_AI_DATA,
    "scikit-learn": CATEGORY_AI_DATA,
    "sklearn": CATEGORY_AI_DATA,
    "keras": CATEGORY_AI_DATA,
    "hugging face": CATEGORY_AI_DATA,
    "langchain": CATEGORY_AI_DATA,
    "langgraph": CATEGORY_AI_DATA,
    "retrieval-augmented generation": CATEGORY_AI_DATA,
    "rag": CATEGORY_AI_DATA,
    "rag pipelines": CATEGORY_AI_DATA,
    "llms": CATEGORY_AI_DATA,
    "llm": CATEGORY_AI_DATA,
    "llm apis": CATEGORY_AI_DATA,
    "large language models": CATEGORY_AI_DATA,
    "llama": CATEGORY_AI_DATA,
    "vector search": CATEGORY_AI_DATA,
    "semantic search": CATEGORY_AI_DATA,
    "natural language processing": CATEGORY_AI_DATA,
    "nlp": CATEGORY_AI_DATA,
    "deep learning": CATEGORY_AI_DATA,
    "optical character recognition": CATEGORY_AI_DATA,
    "ocr": CATEGORY_AI_DATA,
    "chromadb": CATEGORY_AI_DATA,
    "chroma": CATEGORY_AI_DATA,
    "sentence-transformers": CATEGORY_AI_DATA,
    "sentence transformers": CATEGORY_AI_DATA,
    "tensorflow": CATEGORY_AI_DATA,
    "opencv": CATEGORY_AI_DATA,

    # Blockchain
    "solidity": CATEGORY_BLOCKCHAIN,
    "ethereum": CATEGORY_BLOCKCHAIN,
    "smart contracts": CATEGORY_BLOCKCHAIN,
    "smart contract": CATEGORY_BLOCKCHAIN,
    "web3": CATEGORY_BLOCKCHAIN,
    "web3.js": CATEGORY_BLOCKCHAIN,
    "ethers.js": CATEGORY_BLOCKCHAIN,
    "hardhat": CATEGORY_BLOCKCHAIN,
    "truffle": CATEGORY_BLOCKCHAIN,

    # Cloud & DevOps
    "docker": CATEGORY_CLOUD_DEVOPS,
    "amazon web services": CATEGORY_CLOUD_DEVOPS,
    "aws": CATEGORY_CLOUD_DEVOPS,
    "google cloud platform": CATEGORY_CLOUD_DEVOPS,
    "gcp": CATEGORY_CLOUD_DEVOPS,
    "azure": CATEGORY_CLOUD_DEVOPS,
    "ci/cd": CATEGORY_CLOUD_DEVOPS,
    "continuous integration": CATEGORY_CLOUD_DEVOPS,
    "vercel": CATEGORY_CLOUD_DEVOPS,
    "render": CATEGORY_CLOUD_DEVOPS,
    "kubernetes": CATEGORY_CLOUD_DEVOPS,
    "k8s": CATEGORY_CLOUD_DEVOPS,
    "terraform": CATEGORY_CLOUD_DEVOPS,
    "ansible": CATEGORY_CLOUD_DEVOPS,
    "nginx": CATEGORY_CLOUD_DEVOPS,

    # Tools
    "git": CATEGORY_TOOLS,
    "github": CATEGORY_TOOLS,
    "gitlab": CATEGORY_TOOLS,
    "bitbucket": CATEGORY_TOOLS,
    "vs code": CATEGORY_TOOLS,
    "vscode": CATEGORY_TOOLS,
    "postman": CATEGORY_TOOLS,
    "agile": CATEGORY_TOOLS,
    "jira": CATEGORY_TOOLS,
    "linux": CATEGORY_TOOLS,
    "windows": CATEGORY_TOOLS,
    "macos": CATEGORY_TOOLS,
}


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9+.]", "", str(name).strip().lower())


_NORMALIZED_TAXONOMY: dict[str, str] = {
    _normalize_name(k): v for k, v in _KNOWN_SKILL_CATEGORIES.items()
}


CATEGORY_TITLE_MAP: dict[str, str] = {
    "languages": CATEGORY_LANGUAGES,
    "frontend": CATEGORY_FRONTEND,
    "mobile": CATEGORY_MOBILE,
    "backend": CATEGORY_BACKEND,
    "backend & architecture": CATEGORY_BACKEND,
    "backend and architecture": CATEGORY_BACKEND,
    "databases": CATEGORY_DATABASES,
    "cloud_devops": CATEGORY_CLOUD_DEVOPS,
    "cloud & devops": CATEGORY_CLOUD_DEVOPS,
    "cloud and devops": CATEGORY_CLOUD_DEVOPS,
    "cloud": CATEGORY_CLOUD_DEVOPS,
    "devops": CATEGORY_CLOUD_DEVOPS,
    "tools": CATEGORY_TOOLS,
    "ai_ml": CATEGORY_AI_DATA,
    "ai/ml": CATEGORY_AI_DATA,
    "ai/ml & data": CATEGORY_AI_DATA,
    "blockchain": CATEGORY_BLOCKCHAIN,
    "soft": "Soft Skills",
    "soft skills": "Soft Skills",
}


def classify_skill(name: str, existing_category: str | None = None) -> str:
    """Classify a skill name into a canonical resume category.

    If an existing category is provided and is a valid specific category
    (i.e. not generic 'Tools', 'Other', or blank), it is preserved and formatted nicely.
    """
    clean_name = str(name).strip()
    if not clean_name:
        if existing_category and existing_category.strip():
            cat_l = existing_category.strip().lower()
            return CATEGORY_TITLE_MAP.get(cat_l, existing_category.strip())
        return CATEGORY_TOOLS

    # If the caller provided a legitimate specific category, keep it
    if existing_category and existing_category.strip():
        cat_lower = existing_category.strip().lower()
        if cat_lower in CATEGORY_TITLE_MAP and cat_lower not in ("tools", "other", "unknown", "skill", "skills", ""):
            return CATEGORY_TITLE_MAP[cat_lower]
        if cat_lower not in ("tools", "other", "unknown", "skill", "skills", ""):
            return existing_category.strip()

    # Exact or lowercase lookup
    lower_name = clean_name.lower()
    if lower_name in _KNOWN_SKILL_CATEGORIES:
        return _KNOWN_SKILL_CATEGORIES[lower_name]

    # Normalized lookup (strip special characters except +, .)
    norm = _normalize_name(clean_name)
    if norm in _NORMALIZED_TAXONOMY:
        return _NORMALIZED_TAXONOMY[norm]

    # Substring / heuristic matches
    if any(w in lower_name for w in ["database", "sql", "mongo", "postgres"]):
        return CATEGORY_DATABASES
    if any(w in lower_name for w in ["react", "vue", "angular", "css", "html", "frontend"]):
        return CATEGORY_FRONTEND
    if any(w in lower_name for w in ["android", "ios", "flutter", "mobile"]):
        return CATEGORY_MOBILE
    if any(w in lower_name for w in ["node", "express", "api", "backend", "graphql", "microservice"]):
        return CATEGORY_BACKEND
    if any(w in lower_name for w in ["docker", "cloud", "aws", "gcp", "azure", "ci/cd", "devops", "kubernetes"]):
        return CATEGORY_CLOUD_DEVOPS
    if any(w in lower_name for w in ["learning", "neural", "llm", "rag", "ai", "vision", "nlp"]):
        return CATEGORY_AI_DATA
    if any(w in lower_name for w in ["blockchain", "solidity", "smart contract", "crypto"]):
        return CATEGORY_BLOCKCHAIN

    # If existing category was provided (e.g. Tools), retain it; otherwise default to Tools
    if existing_category and existing_category.strip():
        cat_l = existing_category.strip().lower()
        return CATEGORY_TITLE_MAP.get(cat_l, existing_category.strip())
    return CATEGORY_TOOLS
