def _qa_weight_cypher(rel_var: str, binary: bool = False, vote: bool = False, uniform: bool = False) -> str:
    if uniform:  # C-0 (docs/c_0_b_acc_setup.md): every answer weighs 1.0; accepted / score / trustScore are not read
        return "1.0"
    if vote:
        return (f"({VOTE_W_ACCEPTED} * CASE WHEN type({rel_var}) = 'HAS_ACCEPTED_ANSWER' THEN 1.0 ELSE 0.0 END "
                f"+ {VOTE_W_VOTES} * {_vote_norm_cypher()})")
    if binary:
        return f"CASE WHEN type({rel_var}) = 'HAS_ACCEPTED_ANSWER' THEN 1.0 ELSE 0.0 END"
    return f"CASE WHEN type({rel_var}) = 'HAS_ACCEPTED_ANSWER' THEN 1.0 ELSE coalesce(a.trustScore, 0.0) END"
