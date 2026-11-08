"""Multi-turn conversation follow-up resolution and contextual query rewriting.

Specifications:
- Spec §5 T2, T4
- TC-T4-06: 3-turn follow-up context resolution
- BM_FU_DEV_01..03: Carrying explicit periods and contextual entities
"""

from datetime import date
import re
import unicodedata
from typing import Any

from app.agents.llm_text import DeterministicTemplateTextClient, TextLLMClient
from app.memory.session_store import TurnRecord


def remove_accents(input_str: str) -> str:
    """Normalize and strip diacritics from Vietnamese text for robust keyword matching."""
    nfkd = unicodedata.normalize("NFKD", input_str)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])


FOLLOWUP_CUE_PATTERNS = [
    r"c[oò]n\s+th[aá]ng\s+tr[uư][oớ]c",
    r"th[aá]ng\s+tr[uư][oớ]c",
    r"k[yỳ]\s+tr[uư][oớ]c",
    r"gi[aả]m\s+bao\s+nhi[eê]u",
    r"t[aă]ng\s+bao\s+nhi[eê]u",
    r"thay\s+[đd][oổ]i\s+bao\s+nhi[eê]u",
    r"th[aá]ng\s+[đd][oó]",
    r"k[yỳ]\s+[đd][oó]",
    r"trong\s+th[aá]ng\s+[đd][oó]",
    r"t[aạ]i\s+sao\s+th[aá]ng",
    r"c[oò]n\s+d[aà]i\s+h[aạ]n",
    r"c[oò]n\s+n[oợ]\s+d[aà]i\s+h[aạ]n",
    r"bao\s+nhi[eê]u\s*%",
    r"bao\s+nhi[eê]u\s+ph[aầ]n\s+tr[aă]m",
    r"chi[eế]m\s+bao\s+nhi[eê]u",
]


def detect_followup_cues(query: str) -> list[str]:
    """Detect whether query contains conversational follow-up cues."""
    found: list[str] = []
    q_norm = query.lower()
    for pat in FOLLOWUP_CUE_PATTERNS:
        match = re.search(pat, q_norm, re.IGNORECASE)
        if match:
            found.append(match.group(0))
    return found


def extract_period_from_history(history: list[TurnRecord]) -> str | None:
    """Extract explicit date/month mentioned in prior conversation turns."""
    for turn in reversed(history):
        text = f"{turn.standalone_query or ''} {turn.query}"
        # Match 'tháng M năm YYYY' or 'tháng M/YYYY' or 'MM/YYYY' or 'YYYY-MM'
        m = re.search(r"th[aá]ng\s+(\d{1,2})\s+n[aă]m\s+(\d{4})", text, re.IGNORECASE)
        if m:
            return f"tháng {m.group(1)} năm {m.group(2)}"
        m2 = re.search(r"th[aá]ng\s+(\d{1,2})/(\d{4})", text, re.IGNORECASE)
        if m2:
            return f"tháng {m2.group(1)}/{m2.group(2)}"
        m3 = re.search(r"\b(0[1-9]|1[0-2])/(\d{4})\b", text)
        if m3:
            return f"{m3.group(1)}/{m3.group(2)}"
        m4 = re.search(r"\b(\d{4})-(0[1-9]|1[0-2])\b", text)
        if m4:
            return f"{m4.group(2)}/{m4.group(1)}"
    return None


def resolve_followup_query(
    query: str,
    history: list[TurnRecord],
    as_of_date: date = date(2026, 7, 31),
    data_profile: str = "real",
    llm_client: TextLLMClient | None = None,
) -> tuple[str, bool, list[str]]:
    """Resolve anaphoric follow-up query against conversational history.

    Returns:
        tuple[str, bool, list[str]]: (standalone_query, is_followup, detected_cues)
    """
    if not history:
        return query, False, []

    cues = detect_followup_cues(query)
    if not cues:
        return query, False, []

    last_turn = history[-1]
    last_text = f"{last_turn.standalone_query or ''} {last_turn.query}"
    last_text_lower = last_text.lower()
    last_text_unaccent = remove_accents(last_text_lower)

    # 1. Topic detection from history
    is_short_term_debt = (
        "34111" in last_text_lower
        or "dư nợ ngắn hạn" in last_text_lower
        or "du no ngan han" in last_text_unaccent
        or ("du_no_ngan_han" in (last_turn.kpi_keys or []))
    )
    is_long_term_debt = (
        "34112" in last_text_lower
        or "dư nợ dài hạn" in last_text_lower
        or "du no dai han" in last_text_unaccent
        or ("du_no_dai_han" in (last_turn.kpi_keys or []))
    )
    is_cashflow = (
        "dòng tiền" in last_text_lower
        or "dong tien" in last_text_unaccent
        or ("dong_tien" in (last_turn.kpi_keys or []))
    )
    is_inventory = (
        "tồn kho" in last_text_lower
        or "ton kho" in last_text_unaccent
        or ("hang_ton_kho" in (last_turn.kpi_keys or []))
    )
    is_credit_limit = (
        "hạn mức" in last_text_lower
        or "han muc" in last_text_unaccent
        or ("ty_le_su_dung_han_muc" in (last_turn.kpi_keys or []))
    )

    q_lower = query.lower()
    q_unaccent = remove_accents(q_lower)

    # Calculate anchored dates
    cur_m = as_of_date.month
    cur_y = as_of_date.year
    prev_m = cur_m - 1 if cur_m > 1 else 12
    prev_y = cur_y if cur_m > 1 else cur_y - 1
    cur_month_str = f"{cur_m:02d}/{cur_y}"
    prev_month_str = f"{prev_m:02d}/{prev_y}"

    hist_period = extract_period_from_history(history)
    has_synth_context = "mô phỏng" in last_text_lower or "synth" in last_text_lower or data_profile == "synth"

    # --- Rule Case A: Asking about previous month ("Còn tháng trước?", "Tháng trước thế nào?") ---
    if re.search(r"(c[oò]n\s+th[aá]ng\s+tr[uư][oớ]c|th[aá]ng\s+tr[uư][oớ]c|k[yỳ]\s+tr[uư][oớ]c)", q_lower):
        if is_short_term_debt:
            rewritten = f"Tổng dư nợ ngắn hạn của công ty trong tháng {prev_month_str} là bao nhiêu?"
            return rewritten, True, cues
        elif is_long_term_debt:
            rewritten = f"Tổng dư nợ dài hạn của công ty trong tháng {prev_month_str} là bao nhiêu?"
            return rewritten, True, cues
        elif is_inventory:
            rewritten = f"Tổng giá trị hàng tồn kho của công ty trong tháng {prev_month_str} là bao nhiêu?"
            return rewritten, True, cues
        elif is_cashflow:
            rewritten = f"Dòng tiền thuần của công ty trong tháng {prev_month_str} là bao nhiêu?"
            return rewritten, True, cues

    # --- Rule Case B: Asking about percentage change / MoM change ("Giảm bao nhiêu %?", "Tăng bao nhiêu %?") ---
    if re.search(r"(gi[aả]m\s+bao\s+nhi[eê]u|t[aă]ng\s+bao\s+nhi[eê]u|thay\s+[đd][oổ]i\s+bao\s+nhi[eê]u|bao\s+nhi[eê]u\s*%|bao\s+nhi[eê]u\s+ph[aầ]n\s+tr[aă]m)", q_lower):
        if is_short_term_debt:
            rewritten = f"Tỷ lệ phần trăm thay đổi giảm dư nợ ngắn hạn giữa tháng {cur_month_str} và tháng {prev_month_str} là bao nhiêu %?"
            return rewritten, True, cues
        elif is_long_term_debt:
            rewritten = f"Tỷ lệ phần trăm thay đổi dư nợ dài hạn giữa tháng {cur_month_str} và tháng {prev_month_str} là bao nhiêu %?"
            return rewritten, True, cues
        elif is_inventory:
            rewritten = f"Tỷ lệ phần trăm thay đổi giá trị hàng tồn kho giữa tháng {cur_month_str} và tháng {prev_month_str} là bao nhiêu %?"
            return rewritten, True, cues

    # --- Rule Case C: Query referencing "tháng đó" / "kỳ đó" with explicit historical period ---
    if re.search(r"(th[aá]ng\s+[đd][oó]|k[yỳ]\s+[đd][oó]|trong\s+th[aá]ng\s+[đd][oó])", q_lower) and hist_period:
        rewritten = re.sub(
            r"th[aá]ng\s+[đd][oó]|k[yỳ]\s+[đd][oó]",
            hist_period,
            query,
            flags=re.IGNORECASE,
        )
        if has_synth_context and "mô phỏng" not in rewritten.lower():
            rewritten = rewritten.rstrip(" ?.") + " trên hệ thống mô phỏng?"
        return rewritten, True, cues

    # --- Rule Case D: "Còn dài hạn?" / "Còn nợ dài hạn?" ---
    if re.search(r"(c[oò]n\s+d[aà]i\s+h[aạ]n|c[oò]n\s+n[oợ]\s+d[aà]i\s+h[aạ]n)", q_lower):
        rewritten = "Tổng dư nợ dài hạn tại các ngân hàng hiện tại là bao nhiêu?"
        return rewritten, True, cues

    # --- Rule Case E: Carrying "tại sao tháng M" with topic from history ---
    if re.search(r"t[aạ]i\s+sao\s+th[aá]ng\s+\d+", q_lower):
        rewritten = query
        if is_cashflow and "dòng tiền" not in rewritten.lower():
            rewritten = rewritten.replace("tháng", "dòng tiền tháng")
        if has_synth_context and "mô phỏng" not in rewritten.lower():
            rewritten = rewritten.rstrip(" ?.") + " trên hệ thống mô phỏng?"
        return rewritten, True, cues

    # LLM rewrite attempt if client provided
    if llm_client is not None and not isinstance(llm_client, DeterministicTemplateTextClient):
        hist_turns = history[-5:]
        formatted_hist = "\n".join([
            f"User: {t.query}\nAssistant: {(t.answer or {}).get('summary', '')}"
            for t in hist_turns
        ])
        prompt = (
            f"<conversation_history>\n{formatted_hist}\n</conversation_history>\n"
            f"Câu hỏi tiếp theo của người dùng: {query}\n"
            f"Hãy viết lại câu hỏi trên thành một câu hỏi độc lập duy nhất, đầy đủ ngữ cảnh bằng tiếng Việt."
        )
        try:
            candidate = llm_client.generate_text(
                system_prompt="Bạn là trợ lý giải quyết ngữ cảnh hội thoại tiếng Việt. Viết lại câu hỏi đầy đủ.",
                user_prompt=prompt,
            ).strip()
            if candidate and len(candidate) > len(query) and not candidate.startswith("???"):
                return candidate, True, cues
        except Exception:
            pass

    # Generic fallback: append last topic
    if is_short_term_debt:
        return f"{query.rstrip(' ?.')} liên quan đến dư nợ ngắn hạn?", True, cues
    if is_cashflow:
        return f"{query.rstrip(' ?.')} liên quan đến dòng tiền?", True, cues

    return query, True, cues
