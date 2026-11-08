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
PLAYBOOKS_FILE = KNOWLEDGE_DIR / "cfo_playbooks.yaml"
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
def load_cfo_playbooks(path: Optional[Path] = None) -> dict:
    """Load CFO playbooks and seasonality configuration from YAML file."""
    target_path = path or PLAYBOOKS_FILE
    with open(target_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_seasonality_insight(month: int) -> str:
    """Return wood industry seasonality insight for a given month (1..12)."""
    playbooks = load_cfo_playbooks()
    seasonality = playbooks.get("seasonality", {})
    if 1 <= month <= 3:
        return seasonality.get("Q1", {}).get(
            "insight",
            "Chu kỳ Q1 ngành gỗ: Thấp điểm sau Tết Nguyên Đán, các công trình mới khởi công, dòng tiền chậm, cần duy trì đệm tiền mặt an toàn.",
        )
    elif 4 <= month <= 8:
        return seasonality.get("Q2_Q3", {}).get(
            "insight",
            "Chu kỳ Q2-Q3 ngành gỗ: Giai đoạn tích trữ nguyên liệu ván thô và sản xuất, DIO có xu hướng tăng cao, tận dụng vốn vay ngân hàng.",
        )
    elif 9 <= month <= 12:
        return seasonality.get("Q4", {}).get(
            "insight",
            "Chu kỳ Q4 ngành gỗ: Cao điểm bàn giao nội thất đón Tết, doanh thu đạt đỉnh, cần siết chặt thu hồi công nợ và kiểm soát DSO.",
        )
    return "Chu kỳ kinh doanh ngành gỗ Minh Long."


def match_cfo_playbooks(kpi_values: dict[str, float]) -> list[dict]:
    """Match active CFO SOP playbooks based on operational KPI trigger conditions."""
    playbooks_data = load_cfo_playbooks().get("playbooks", {})
    matched: list[dict] = []

    # SOP-01: Cash Crunch SOP
    # dong_tien_rong < 0 OR cash_runway < 1.5
    if "dong_tien_rong" in kpi_values or "cash_runway" in kpi_values:
        net_cf = kpi_values.get("dong_tien_rong")
        runway = kpi_values.get("cash_runway")
        is_triggered = False
        if net_cf is not None and net_cf < 0:
            is_triggered = True
        if runway is not None and runway < 1.5:
            is_triggered = True
        if is_triggered and "SOP-01" in playbooks_data:
            matched.append(playbooks_data["SOP-01"])

    # SOP-02: Excess Liquidity SOP
    # cash_runway > 3.5 AND tien_va_tuong_duong_tien > 20,000,000,000
    if "cash_runway" in kpi_values or "tien_va_tuong_duong_tien" in kpi_values:
        runway = kpi_values.get("cash_runway")
        cash_bal = kpi_values.get("tien_va_tuong_duong_tien")
        is_triggered = False
        if runway is not None and runway > 3.5 and cash_bal is not None and cash_bal > 20_000_000_000.0:
            is_triggered = True
        elif cash_bal is not None and cash_bal > 20_000_000_000.0 and runway is None:
            is_triggered = False
        if is_triggered and "SOP-02" in playbooks_data:
            matched.append(playbooks_data["SOP-02"])

    # SOP-03: AR Overdue Crisis SOP
    # dso > 60 OR ty_le_no_qua_han > 0.15 OR vong_quay_phai_thu_nam < 2.0 OR vong_quay_phai_thu_hien_tai < 1.0
    if any(k in kpi_values for k in ["dso", "ty_le_no_qua_han", "vong_quay_phai_thu_nam", "vong_quay_phai_thu_hien_tai"]):
        dso = kpi_values.get("dso")
        overdue_ratio = kpi_values.get("ty_le_no_qua_han")
        ar_turnover_yr = kpi_values.get("vong_quay_phai_thu_nam")
        ar_turnover_cur = kpi_values.get("vong_quay_phai_thu_hien_tai")
        is_triggered = False
        if dso is not None and dso > 60:
            is_triggered = True
        if overdue_ratio is not None and overdue_ratio > 0.15:
            is_triggered = True
        if ar_turnover_yr is not None and ar_turnover_yr < 2.0:
            is_triggered = True
        if ar_turnover_cur is not None and ar_turnover_cur < 1.0:
            is_triggered = True
        if is_triggered and "SOP-03" in playbooks_data:
            matched.append(playbooks_data["SOP-03"])

    # SOP-04: Slow-Moving Inventory SOP
    # dio > 90 OR vong_quay_hang_ton_kho < 1.0 OR ty_le_ton_kho_tren_doanh_thu > 4.0 OR tang_ton_kho_melamine > 0.25
    if any(k in kpi_values for k in ["dio", "vong_quay_hang_ton_kho", "ty_le_ton_kho_tren_doanh_thu", "tang_ton_kho_melamine"]):
        dio = kpi_values.get("dio")
        inv_turnover = kpi_values.get("vong_quay_hang_ton_kho")
        inv_rev_ratio = kpi_values.get("ty_le_ton_kho_tren_doanh_thu")
        melamine_growth = kpi_values.get("tang_ton_kho_melamine")
        is_triggered = False
        if dio is not None and dio > 90:
            is_triggered = True
        if inv_turnover is not None and inv_turnover < 1.0:
            is_triggered = True
        if inv_rev_ratio is not None and inv_rev_ratio > 4.0:
            is_triggered = True
        if melamine_growth is not None and melamine_growth > 0.25:
            is_triggered = True
        if is_triggered and "SOP-04" in playbooks_data:
            matched.append(playbooks_data["SOP-04"])

    return matched


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
