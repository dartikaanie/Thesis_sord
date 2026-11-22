def claim_stats(records: list[dict]) -> dict:
    """From usable, attempted judge records: unverifiable-claim share and the faithfulness / citation-support
    aggregates. Denominators (docs/OFFICIAL_RUN_MATRIX.md):
      unverifiable  = UNVERIFIABLE claims / all claims
      faithfulness  = claims with supported_by_context == YES / claims with a YES or NO value (micro, over claims);
                      macro = mean over answers of the same ratio (answers with >= 1 rated claim)
      citation_sup. = cited claims with cited_item_supports == YES / cited claims with a YES or NO value
    Claims with a null value are left out of the denominator, never imputed."""
    n_claims = n_unv = f_yes = f_n = c_yes = c_n = 0
    f_macro, c_macro = [], []
    for r in records:
        if is_unusable(r) or not r.get("answer_attempted"):
            continue
        fy = fn = cy = cn = 0
        for cl in r.get("claims") or []:
            n_claims += 1
            n_unv += str(cl.get("verdict", "")).upper() == "UNVERIFIABLE"
            sup = str(cl.get("supported_by_context") or "").upper()
            if sup in ("YES", "NO"):
                fn += 1
                fy += sup == "YES"
            cs = str(cl.get("cited_item_supports") or "").upper()
            if cs in ("YES", "NO"):
                cn += 1
                cy += cs == "YES"
        f_yes, f_n, c_yes, c_n = f_yes + fy, f_n + fn, c_yes + cy, c_n + cn
        if fn:
            f_macro.append(fy / fn)
        if cn:
            c_macro.append(cy / cn)
    mean = lambda xs: round(sum(xs) / len(xs), 4) if xs else None  # noqa: E731
    return {"n_claims": n_claims, "n_unverifiable": n_unv, "unverifiable_share": _ratio(n_unv, n_claims),
            "faithfulness": {"micro": _ratio(f_yes, f_n), "n_claims_rated": f_n, "macro": mean(f_macro),
                             "n_answers": len(f_macro)},
            "citation_support": {"micro": _ratio(c_yes, c_n), "n_claims_cited": c_n, "macro": mean(c_macro),
                                 "n_answers": len(c_macro)}}
