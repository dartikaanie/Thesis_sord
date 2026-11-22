def panel_category(panel_label: str) -> str | None:
    """Panel label -> judge_binary's 3-category scale (ABSTAIN / NOT_HALLUCINATED / HALLUCINATED);
    None for UNRESOLVED."""
    if panel_label == UNRESOLVED:
        return None
    if panel_label == ABSTAIN:
        return "ABSTAIN"
    return "HALLUCINATED" if panel_label in HALLUCINATED_LABELS else "NOT_HALLUCINATED"
