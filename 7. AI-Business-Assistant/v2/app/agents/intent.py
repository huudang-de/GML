"""Intent classification agent with LLM parsing, strict validation, and heuristic fallback.

Specifications:
- Spec §5 T4, §11.7
- TC-T4-01, TC-T4-02, TC-T4-03, TC-T4-04
- EV-11 (Intent routing evaluation target M-11 >= 95%)
"""

import json
import logging
import re
import unicodedata
from typing import Any

from app.agents.llm_text import DeterministicTemplateTextClient, TextLLMClient
from app.core.security import get_allowed_views
from app.orchestration.state import Intent

logger = logging.getLogger(__name__)

VALID_INTENTS: set[Intent] = {"sql_only", "rag_only", "both", "alert", "blocked"}


def remove_accents(input_str: str) -> str:
    """Normalize and strip accents for robust matching."""
    nfkd = unicodedata.normalize("NFKD", input_str)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])


def classify_intent_heuristic(query: str, role: str | None = None) -> Intent:
    """Deterministic rule-based intent classification for all 5 intent states."""
    q = query.lower().strip()
    q_unaccent = remove_accents(q)

    # 1. Blocked intent check (DML / DDL / Prompt Injection / Credential Theft / RBAC)
    destructive_keywords = [
        "insert into", "delete from", "drop table", "alter table", "update ",
        "thêm dữ liệu", "them du lieu", "xoá dữ liệu", "xoa du lieu",
        "sửa dữ liệu", "sua du lieu", "cập nhật dữ liệu", "cap nhat du lieu",
        "thay đổi mật khẩu", "reset password", "truncate ",
        "xoá bảng", "xoa bang", "phá hủy dữ liệu", "pha huy du lieu",
        "bỏ qua các chỉ dẫn", "bo qua cac chi dan",
        "bỏ qua mọi hướng dẫn", "bo qua moi huong dan",
        "ignore previous instructions", "ignore all instructions",
        "system prompt", "mật khẩu kết nối", "mat khau ket noi",
        "mật khẩu db", "mat khau db", "password database",
    ]
    if any(kw in q for kw in destructive_keywords) or any(kw in q_unaccent for kw in destructive_keywords):
        return "blocked"

    # RBAC domain violation check
    if role:
        allowed = get_allowed_views(role)
        if not allowed:
            return "blocked"
        if role == "quan_ly_kho":
            # Warehouse manager only has ai_v_ton_kho; blocked on debt/loan/cash/bctc
            financial_terms = [
                "dư nợ", "du no", "nợ vay", "no vay", "ngân hàng", "ngan hang",
                "hạn mức", "han muc", "tiền gửi", "tien gui", "dòng tiền", "dong tien",
                "công nợ", "cong no", "phải thu", "phai thu", "phải trả", "phai tra",
                "bctc", "báo cáo tài chính", "bao cao tai chinh", "lợi nhuận", "loi nhuan",
                "doanh thu", "doanh so",
            ]
            if any(ft in q for ft in financial_terms) or any(ft in q_unaccent for ft in financial_terms):
                return "blocked"

    # 2. Alert intent check (Active threshold & anomaly alerts)
    alert_keywords = [
        "cảnh báo gì", "canh bao gi", "danh sách cảnh báo", "danh sach canh bao",
        "cảnh báo đang mở", "canh bao dang mo", "alert nào", "alert nao",
        "có cảnh báo nào", "co canh bao nao", "xem cảnh báo", "xem canh bao",
    ]
    is_asking_threshold_rule = any(
        kw in q or kw in q_unaccent
        for kw in ["ngưỡng cảnh báo là bao nhiêu", "nguong canh bao la bao nhieu", "công thức cảnh báo", "quy định cảnh báo"]
    )
    if any(kw in q for kw in alert_keywords) and not is_asking_threshold_rule:
        return "alert"

    # 3. Check for quantitative clause
    has_quant_clause = any(
        kw in q or kw in q_unaccent
        for kw in ["là bao nhiêu", "la bao nhieu", "hiện tại", "hien tai", "hiện nay", "hien nay", "đạt bao nhiêu", "dat bao nhieu", "chiếm bao nhiêu", "chiem bao nhieu"]
    )

    # 4. Both intent check (compound quantitative + qualitative/policy/strategy/collateral)
    both_causal = [
        "tại sao", "tai sao", "vì sao", "vi sao",
        "quy định xử lý", "quy dinh xu ly",
        "chiến lược", "chien luoc",
        "lý do", "ly do", "nguyên nhân", "nguyen nhan",
        "giải thích nguyên nhân", "giai thich nguyen nhan",
        "giải thích cảnh báo", "giai thich canh bao",
        "kích hoạt cảnh báo gì", "kich hoat canh bao gi",
    ]
    if any(kw in q for kw in both_causal) or any(kw in q_unaccent for kw in both_causal):
        return "both"

    has_qual_clause = any(
        kw in q or kw in q_unaccent
        for kw in [
            "tài sản bảo đảm nào", "tai san bao dam nao", "thế chấp chủ yếu", "the chap chu yeu",
            "tỷ trọng thế nào", "ty trong the nao", "chiếm tỷ trọng thế nào",
            "quy trình đốc thúc", "quy trinh doc thuc", "quy trình thu hồi", "quy trinh thu hoi",
            "ngân hàng nào đang có lãi suất huy động cao nhất", "lãi suất huy động cao nhất",
            "giải pháp cân đối", "giai phap can doi", "nguồn tiền thâm hụt", "nguon tien tham hut",
            "phản ánh chiến lược", "phan anh chien luoc",
        ]
    )
    if has_quant_clause and has_qual_clause:
        return "both"

    # 5. RAG only intent check (definitions, formulas, SOPs, guidelines, policies)
    rag_keywords = [
        "công thức", "cong thuc", "định nghĩa", "dinh nghia",
        "tính thế nào", "tinh the nao", "cách tính", "cach tinh",
        "quy trình", "quy trinh", "chính sách", "chinh sach",
        "hướng dẫn", "huong dan", "tài liệu", "tai lieu",
        "cẩm nang", "cam nang", "story telling",
        "tiêu chí phân loại", "tieu chi phan loai",
        "nguyên tắc", "nguyen tac", "cách phân loại", "cach phan loai",
        "ngưỡng cảnh báo", "nguong canh bao",
        "quy định", "quy dinh",
        "kịch bản ứng phó", "kich ban ung pho",
    ]
    if any(kw in q for kw in rag_keywords) or any(kw in q_unaccent for kw in rag_keywords):
        return "rag_only"

    # 6. Default to sql_only
    return "sql_only"


def classify_intent(
    query: str,
    role: str = "ceo",
    llm_client: TextLLMClient | None = None,
) -> tuple[Intent, list[str]]:
    """Classify user query intent into one of 5 intents.

    Returns:
        tuple[Intent, list[str]]: (intent, warnings_or_errors)
    """
    if llm_client is None or isinstance(llm_client, DeterministicTemplateTextClient):
        return classify_intent_heuristic(query=query, role=role), []

    # LLM-based intent classification with structured JSON output
    prompt = (
        "Phân loại ý định (intent) của câu hỏi kinh doanh/tài chính sau thành một trong 5 giá trị:\n"
        "- 'sql_only': truy vấn số liệu kế toán/tài chính từ cơ sở dữ liệu\n"
        "- 'rag_only': tra cứu công thức, định nghĩa, quy trình, chính sách, tài liệu tri thức\n"
        "- 'both': câu hỏi kết hợp cả số liệu và quy trình/giải thích nguyên nhân/chiến lược\n"
        "- 'alert': tra cứu danh sách cảnh báo hoặc tình trạng cảnh báo đang mở\n"
        "- 'blocked': thao tác sửa/xoá dữ liệu (DML/DDL), tiêm prompt (injection), hoặc vi phạm phân quyền\n\n"
        f"Vai trò người dùng: {role}\n"
        f"Câu hỏi: \"{query}\"\n\n"
        "Trả về DUY NHẤT một JSON hợp lệ dạng: {\"intent\": \"<intent_value>\"}"
    )

    try:
        response_text = llm_client.generate_text(
            system_prompt="Bạn là chuyên gia phân loại ý định hệ thống AI doanh nghiệp. Trả về đúng format JSON.",
            user_prompt=prompt,
        ).strip()

        # Parse JSON
        m = re.search(r"\{.*\}", response_text, re.DOTALL)
        if not m:
            raise ValueError(f"No JSON object found in response: '{response_text}'")

        data = json.loads(m.group(0))
        intent_val = str(data.get("intent", "")).lower().strip()

        if intent_val in VALID_INTENTS:
            return intent_val, []  # type: ignore

        raise ValueError(f"Invalid intent enum value: '{intent_val}'")

    except Exception as e:
        fallback_intent = classify_intent_heuristic(query=query, role=role)
        err_msg = f"INTENT_LLM_FALLBACK: {e} -> fallback to '{fallback_intent}'"
        logger.warning(err_msg)
        return fallback_intent, [err_msg]
