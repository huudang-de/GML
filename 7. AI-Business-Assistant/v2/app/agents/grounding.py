"""Vietnamese Numerical Grounding Guard and Untrusted Context Sanitizer.

Specifications:
- Spec Phần II §6 (Agent Architecture)
- TC-T3-08 & M-08 (Zero Hallucinated Numbers Gate)
- Review Focus #1: Handle Vietnamese number formats (dots for thousands, commas for decimals),
  multipliers (tỷ, triệu, nghìn, %), dates, citations, form codes, and whitelisted identifiers.
- Review Focus #4: Wrap untrusted context and sanitize fake closing tags.
"""

import math
import re
from typing import Any
from pydantic import BaseModel, Field

from app.agents.models import GroundingVerdict


class ExtractedNumber(BaseModel):
    """Structured representation of a numerical token found in text."""

    raw_text: str
    base_value: float
    unit: str | None = None
    candidates: list[float] = Field(default_factory=list)


def wrap_untrusted_context(tag: str = "untrusted_document_context", content: str | None = None) -> str:
    """Wrap untrusted document content in XML tags and sanitize any fake closing tags."""
    if content is None:
        actual_tag = "untrusted_document_context"
        actual_content = tag
    else:
        actual_tag = tag
        actual_content = content

    # Sanitize fake closing tags </actual_tag> inside actual_content (Review Focus #4)
    pattern = re.compile(rf"</\s*{re.escape(actual_tag)}\s*>", re.IGNORECASE)
    sanitized = pattern.sub(f"&lt;/{actual_tag}&gt;", actual_content)
    return f"<{actual_tag}>\n{sanitized}\n</{actual_tag}>"


def parse_vietnamese_base_number(sign_str: str, num_str: str) -> list[float]:
    """Parse a Vietnamese formatted number string into float candidates."""
    cleaned = num_str.strip().replace(" ", "")
    base_values: list[float] = []

    if "." in cleaned and "," in cleaned:
        last_dot = cleaned.rfind(".")
        last_comma = cleaned.rfind(",")
        if last_comma > last_dot:
            # 1.234.567,89 -> dot is thousand separator, comma is decimal
            std = cleaned.replace(".", "").replace(",", ".")
            base_values.append(float(std))
        else:
            # 1,234,567.89 -> comma is thousand separator, dot is decimal
            std = cleaned.replace(",", "")
            base_values.append(float(std))
    elif "." in cleaned:
        parts = cleaned.split(".")
        if len(parts) > 2:
            # 236.065.233.815 -> thousand separators
            base_values.append(float(cleaned.replace(".", "")))
        elif len(parts) == 2:
            if len(parts[1]) == 3:
                # 3 digits after dot, e.g. 100.000 -> could be 100000 or 100.0
                base_values.append(float(cleaned.replace(".", "")))
                base_values.append(float(cleaned))
            else:
                # e.g. 236.07 or 0.70 -> decimal
                base_values.append(float(cleaned))
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts) > 2:
            # 236,065,233,815 -> thousand separators
            base_values.append(float(cleaned.replace(",", "")))
        elif len(parts) == 2:
            if len(parts[1]) == 3:
                # 3 digits after comma, e.g. 100,000 -> could be 100000 or 100.0
                base_values.append(float(cleaned.replace(",", "")))
                base_values.append(float(cleaned.replace(",", ".")))
            else:
                # e.g. 236,07 or 91,82 -> decimal
                base_values.append(float(cleaned.replace(",", ".")))
    else:
        base_values.append(float(cleaned))

    if sign_str == "-":
        base_values = [-v for v in base_values]

    return base_values


def extract_vietnamese_numbers(
    text: str,
    whitelisted_identifiers: set[str] | None = None,
) -> list[ExtractedNumber]:
    """Extract financial numbers and their multipliers, ignoring non-financial patterns."""
    t = text

    # Step 1: Strip non-financial patterns (Review Focus #1)
    # Citations [1], [2], etc.
    t = re.sub(r"\[\d+\]", " ", t)

    # Dates
    t = re.sub(r"\b\d{1,2}/\d{1,2}/\d{4}\b", " ", t)
    t = re.sub(r"\b\d{1,2}/\d{4}\b", " ", t)
    t = re.sub(r"\b\d{4}-\d{2}(?:-\d{2})?\b", " ", t)
    t = re.sub(r"\b(?:năm|nam)\s+\d{4}\b", " ", t, flags=re.I)
    t = re.sub(r"\b(?:tháng|thang)\s+\d{1,2}\b", " ", t, flags=re.I)
    t = re.sub(r"\b(?:quý|quy)\s+[1-4]\b", " ", t, flags=re.I)
    t = re.sub(r"\bQ[1-4]\b", " ", t, flags=re.I)

    # Form codes and benchmark / test indicators
    t = re.sub(r"\bB0[12]-DN(?:_\d+)?\b", " ", t, flags=re.I)
    t = re.sub(r"\bGQ_\w+\b", " ", t, flags=re.I)
    t = re.sub(r"\bAL-\d+\b", " ", t, flags=re.I)
    t = re.sub(r"\bD[1-5]\b", " ", t)
    t = re.sub(r"\b(?:TC-)?T\d+(?:-\d+)?\b", " ", t, flags=re.I)
    t = re.sub(r"\bM-\d+\b", " ", t, flags=re.I)
    t = re.sub(r"§\s*\d+(?:\.\d+)*", " ", t)

    # Whitelisted accounting identifiers (e.g. 34111, 34113, 34114)
    if whitelisted_identifiers:
        for ident in sorted(whitelisted_identifiers, key=len, reverse=True):
            if ident.strip():
                t = re.sub(rf"\b{re.escape(ident.strip())}\b", " ", t)

    # Step 2: Regex scanner for numbers with optional units
    pattern = re.compile(
        r"""
        (?<!\w)
        (?P<sign>[-+]?)
        (?P<number>
            \d{1,3}(?:\.\d{3})+(?:,\d+)?
            |
            \d{1,3}(?:,\d{3})+(?:\.\d+)?
            |
            \d+[,.]\d+
            |
            \d+
        )
        (?:\s*
            (?P<unit>
                tỷ|ty|triệu|trieu|nghìn|ngàn|%|phần\s+trăm|phan\s+tram
            )
        )?
        (?!\w)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    extracted: list[ExtractedNumber] = []
    for m in pattern.finditer(t):
        raw = m.group(0).strip()
        sign_str = m.group("sign") or ""
        num_str = m.group("number")
        unit_str = m.group("unit")

        try:
            base_vals = parse_vietnamese_base_number(sign_str, num_str)
        except Exception:
            continue

        candidates: set[float] = set()
        unit_clean = (unit_str or "").lower().strip()

        for b in base_vals:
            if unit_clean in ["tỷ", "ty"]:
                candidates.add(b)
                candidates.add(b * 1e9)
            elif unit_clean in ["triệu", "trieu"]:
                candidates.add(b)
                candidates.add(b * 1e6)
            elif unit_clean in ["nghìn", "ngàn"]:
                candidates.add(b)
                candidates.add(b * 1e3)
            elif unit_clean in ["%", "phần trăm", "phan tram"]:
                candidates.add(b)
                candidates.add(b / 100.0)
            else:
                candidates.add(b)

        extracted.append(
            ExtractedNumber(
                raw_text=raw,
                base_value=base_vals[0],
                unit=unit_str,
                candidates=sorted(list(candidates)),
            )
        )

    return extracted


def verify_numerical_grounding(
    text: str,
    allowed_values: list[float],
    whitelisted_identifiers: set[str] | None = None,
    rel_tol: float = 0.015,
    abs_tol: float = 0.05,
) -> GroundingVerdict:
    """Verify that every financial number in text matches at least one allowed value within tolerance."""
    extracted = extract_vietnamese_numbers(text, whitelisted_identifiers=whitelisted_identifiers)
    ungrounded_tokens: list[str] = []

    for item in extracted:
        matched = False
        for c in item.candidates:
            for a in allowed_values:
                if math.isclose(c, a, rel_tol=rel_tol, abs_tol=abs_tol):
                    matched = True
                    break
            if matched:
                break

        if not matched:
            ungrounded_tokens.append(item.raw_text)

    return GroundingVerdict(
        ok=len(ungrounded_tokens) == 0,
        ungrounded_tokens=ungrounded_tokens,
    )
