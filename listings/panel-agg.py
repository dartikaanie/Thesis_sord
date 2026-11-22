def _aggregate_three(labels: list[str]) -> str:
    if sum(1 for lab in labels if lab == ABSTAIN) >= 2:
        return ABSTAIN
    return _resolve({LABEL_OF_SCORE[sorted(s)[1]] for s in product(*(_scores(lab) for lab in labels))})

def _aggregate_two(labels: list[str]) -> str:
    a, b = labels
    if (a == ABSTAIN) != (b == ABSTAIN):
        return UNRESOLVED
    if a == ABSTAIN:
        return ABSTAIN
    if (a in HALLUCINATED_LABELS) != (b in HALLUCINATED_LABELS):
        return UNRESOLVED
    if a not in HALLUCINATED_LABELS:
        return FAKTUAL
    return _resolve({LABEL_OF_SCORE[min(s)] for s in product(_scores(a), _scores(b))})

def aggregate_labels(judge_labels: dict[str, str | None], panel_id: str = "panel-v1") -> dict:
    """`judge_labels`: {judge_id: label, or None for a judge with no valid result (failed call or parse error
    after retries)}. Returns the panel part of the panel record (see module docstring)."""
    for jid, lab in judge_labels.items():
        if lab is not None and lab not in VALID_JUDGE_LABELS:
            raise ValueError(f"judge {jid!r}: unknown label {lab!r}")
    valid = {jid: lab for jid, lab in judge_labels.items() if lab is not None}
    labels = list(valid.values())

    if len(judge_labels) == 3 and len(valid) == 3:
        panel_label, incomplete = _aggregate_three(labels), False
    elif len(valid) == 2:
        panel_label = _aggregate_two(labels)
        incomplete = panel_label != UNRESOLVED
    else:
        panel_label, incomplete = UNRESOLVED, False

    hallucinated = None if panel_label in (UNRESOLVED, ABSTAIN) else panel_label in HALLUCINATED_LABELS
    votes = {lab: labels.count(lab) for lab in VALID_JUDGE_LABELS if lab in labels}
    return {
        "panel_id": panel_id,
        "judge_labels": dict(judge_labels),
        "vote_breakdown": {
            "labels": votes,
            "n_valid": len(valid),
            "n_missing": len(judge_labels) - len(valid),
            "n_abstain": labels.count(ABSTAIN),
            "n_hallucinated": sum(1 for lab in labels if lab in HALLUCINATED_LABELS),
            "n_not_hallucinated": labels.count(FAKTUAL),
        },
        "panel_label": panel_label,
        "panel_hallucinated": hallucinated,
        "panel_abstain": panel_label == ABSTAIN if panel_label != UNRESOLVED else None,
        "panel_incomplete": incomplete,
        "unanimous": len(valid) == 3 and len(judge_labels) == 3 and len(set(labels)) == 1,
    }
