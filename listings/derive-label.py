def derive_label_v2_1(answer_attempted: bool, claims: list[dict]) -> str:
    """Descriptive severity label (the PRIMARY v2.1 label is the binary
    `hallucinated`, see judge_binary.derive_hallucinated):
      not attempted                              -> ABSTAIN
      no CONTRADICTED/FABRICATED claim           -> FAKTUAL
      any error claim with severity CORE         -> HALUSINASI_PENUH
      every error claim has severity MINOR       -> HALUSINASI_SEBAGIAN
      otherwise (an error claim has no severity
      and no CORE error settles it)              -> HALUSINASI_SEVERITY_UNSPECIFIED
    A missing severity is never imputed (Amendment 4 Addendum)."""
    if not answer_attempted:
        return "ABSTAIN"
    errors = [c for c in claims if c.get("verdict") in ERROR_VERDICTS]
    if not errors:
        return "FAKTUAL"
    if any(c.get("severity") == "CORE" for c in errors):
        return "HALUSINASI_PENUH"
    if all(c.get("severity") == "MINOR" for c in errors):
        return "HALUSINASI_SEBAGIAN"
    return "HALUSINASI_SEVERITY_UNSPECIFIED"
