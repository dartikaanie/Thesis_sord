def hallucinated_of(record: dict) -> bool | None:
    """The record's own `hallucinated` field when present (v2.1), else derived (v2)."""
    if "hallucinated" in record:
        return record["hallucinated"]
    return derive_hallucinated(record)

def category_of(record: dict) -> str | None:
    """3-category label used for judge-vs-human agreement: ABSTAIN /
    NOT_HALLUCINATED / HALLUCINATED; None for an unusable record."""
    if is_unusable(record):
        return None
    if record["answer_attempted"] is False:
        return CATEGORY_ABSTAIN
    return CATEGORY_HALLUCINATED if hallucinated_of(record) else CATEGORY_NOT_HALLUCINATED

def severity_of(record: dict) -> str | None:
    """Descriptive severity of a HALLUCINATED record: "PENUH" (any CORE
    error), "SEBAGIAN" (every error claim MINOR), or "UNSPECIFIED" (an
    error claim has no severity and no CORE error settles it -- never
    imputed). None when the record is not hallucinated."""
    if category_of(record) != CATEGORY_HALLUCINATED:
        return None
    errors = [c for c in (record.get("claims") or []) if str(c.get("verdict", "")).upper() in ERROR_VERDICTS]
    severities = [str(c.get("severity") or "").upper() for c in errors]
    if "CORE" in severities:
        return "PENUH"
    if errors and all(s == "MINOR" for s in severities):
        return "SEBAGIAN"
    return "UNSPECIFIED"
