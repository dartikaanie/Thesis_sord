def build_panel_records(metric: str, recs: list[dict], expected: set | None = None) -> list[dict]:
    rows = label_rows_of(metric, recs)
    keys = sorted(expected, key=str) if expected is not None else sorted(rows, key=str)
    out = []
    for k in keys:
        jl = rows.get(k, {j.judge_id: None for j in JUDGES})
        agg = aggregate_key(jl, metric)
        rec = {"metric": metric, "key": list(k), "judge_labels": jl, **agg,
               "panel_score": METRICS[metric]["score"].get(agg["panel_label"])}
        scores = [METRICS[metric]["score"][v] for v in jl.values() if v is not None]
        rec["mean_judge_score"] = round(sum(scores) / len(scores), 4) if len(scores) == 3 else None
        out.append(rec)
    return out
