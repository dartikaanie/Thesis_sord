def _vote_norm_cypher(ans_var: str = "a") -> str:
    d = f"log(1.0 + {VOTE_P99_A})"
    return (f"(CASE WHEN {ans_var}.score IS NULL OR {ans_var}.score <= 0 THEN 0.0 "
            f"WHEN log(1.0 + {ans_var}.score) >= {d} THEN 1.0 ELSE log(1.0 + {ans_var}.score) / {d} END)")
