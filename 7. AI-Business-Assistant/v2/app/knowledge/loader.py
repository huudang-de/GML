"""Knowledge Base Loader and Semantic Matching Service.

Specifications:
- Spec §5 T2 (Semantic Knowledge Layer)
- Review Focus #1: Golden Query filtering by role-based allowed views
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional
import unicodedata
import yaml

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.security import get_allowed_views
from app.knowledge.models import (
    BenchmarkItem,
    BusinessRuleAction,
    GoldenMatch,
    GoldenQuery,
    KpiDefinition,
)

KNOWLEDGE_DIR = Path(__file__).resolve().parent
KPIS_FILE = KNOWLEDGE_DIR / "kpi_definitions.yaml"
RULES_FILE = KNOWLEDGE_DIR / "business_rules.yaml"
GQ_INDEX_FILE = KNOWLEDGE_DIR / "golden_queries" / "index.yaml"
BENCHMARK_FILE = KNOWLEDGE_DIR.parent.parent / "eval" / "benchmark.yaml"


def remove_vietnamese_accents(text: str) -> str:
    """Strip Vietnamese diacritical marks and tone marks."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    return unicodedata.normalize("NFC", text)


def prepare_search_text(text: str) -> str:
    """Normalize text into lower-case NFC and append unaccented representation."""
    nfc = unicodedata.normalize("NFC", text or "").lower().strip()
    unaccented = remove_vietnamese_accents(nfc)
    return f"{nfc} {unaccented}"


@lru_cache(maxsize=1)
def load_kpis(path: Optional[Path] = None) -> dict[str, KpiDefinition]:
    """Load KPI definitions from YAML file into a dictionary keyed by KPI key."""
    target_path = path or KPIS_FILE
    with open(target_path, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f) or {}

    kpis: dict[str, KpiDefinition] = {}
    for key, data in raw_data.items():
        data["key"] = key
        kpis[key] = KpiDefinition(**data)
    return kpis


def get_kpi(key: str) -> KpiDefinition:
    """Retrieve a KPI definition by key, raising KeyError if not found."""
    kpis = load_kpis()
    if key not in kpis:
        raise KeyError(f"KPI key '{key}' not found in knowledge base")
    return kpis[key]


@lru_cache(maxsize=1)
def load_business_rules(path: Optional[Path] = None) -> dict:
    """Load business rules configuration from YAML file."""
    target_path = path or RULES_FILE
    with open(target_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_business_actions(kpi_key: str, level: str) -> dict:
    """Get approved operational actions, authority role, and disclaimer for a KPI threshold."""
    rules = load_business_rules()
    kpi_rules = rules.get(kpi_key, {})
    level_rule = kpi_rules.get(level)
    if not level_rule:
        raise KeyError(f"No business rule found for KPI '{kpi_key}' at level '{level}'")
    action_obj = BusinessRuleAction(**level_rule)
    return action_obj.model_dump()


@lru_cache(maxsize=1)
def load_golden_queries(index_path: Optional[Path] = None) -> list[GoldenQuery]:
    """Load Golden Queries from index.yaml and populate sql_text from SQL files."""
    target_path = index_path or GQ_INDEX_FILE
    with open(target_path, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f) or {}

    queries_data = raw_data.get("queries", [])
    golden_list: list[GoldenQuery] = []
    base_dir = target_path.parent

    for item in queries_data:
        sql_file_name = item.get("sql_file", "")
        sql_path = base_dir / sql_file_name
        if sql_path.exists():
            item["sql_text"] = sql_path.read_text(encoding="utf-8")
        else:
            item["sql_text"] = ""
        golden_list.append(GoldenQuery(**item))

    return golden_list


def load_benchmark(path: Optional[Path] = None) -> list[BenchmarkItem]:
    """Load the 60-item evaluation benchmark from benchmark.yaml."""
    target_path = path or BENCHMARK_FILE
    with open(target_path, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f) or {}

    items_data = raw_data.get("benchmark", [])
    return [BenchmarkItem(**item) for item in items_data]


def match_golden(question: str, role: str = "ceo", k: int = 3) -> list[GoldenMatch]:
    """Find the top-k most semantically similar Golden Queries for a user question.

    Review Focus #1:
    Candidate queries are strictly filtered by get_allowed_views(role).
    A query is only eligible if all views in query.views_used are permitted for the role.

    Similarity is computed using a character/word ngram TF-IDF vectorizer over
    both accented and unaccented representations.
    """
    allowed_views = get_allowed_views(role)
    if not allowed_views:
        return []

    all_queries = load_golden_queries()
    # Filter candidates strictly within role permissions
    candidates = [
        gq for gq in all_queries
        if set(gq.views_used).issubset(allowed_views)
    ]
    if not candidates:
        return []

    # Prepare corpus from candidate question + paraphrases
    corpus = []
    for gq in candidates:
        combined_texts = [gq.question_vi] + gq.paraphrases
        corpus.append(" ".join(prepare_search_text(t) for t in combined_texts))

    # Vectorize candidate corpus and question
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
    tfidf_matrix = vectorizer.fit_transform(corpus)

    q_prep = prepare_search_text(question)
    q_vec = vectorizer.transform([q_prep])

    sims = cosine_similarity(q_vec, tfidf_matrix)[0]

    # Rank candidates by descending similarity
    ranked_indices = sims.argsort()[::-1]
    results: list[GoldenMatch] = []
    for idx in ranked_indices[:k]:
        sim_score = float(sims[idx])
        results.append(GoldenMatch(query=candidates[idx], similarity=sim_score))

    return results
