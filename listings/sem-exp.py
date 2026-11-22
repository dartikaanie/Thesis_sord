def semantic_expansion(driver, database, traversal_candidates: list, index, ids_arr: np.ndarray,
                        sbert_model, n_expansion: int, already_seen_qids: set,
                        exclude_question_ids: set, exclude_answer_ids: set,
                        edge_types: tuple | None = None, stats: dict | None = None,
                        require_answer: bool = False, overfetch: int = EXPANSION_OVERFETCH,
                        trust_weights: bool = False, binary_trust: bool = False,
                        net_score_filter: bool = True, vote_trust: bool = False, uniform_trust: bool = False) -> list:
    """`trust_weights` (v5 only): same answer weight as traverse_graph(trust_weights=True); `binary_trust`/
    `net_score_filter` likewise.

    Ambil s.d. 3 via_question unik dari hasil traversal sbg query baru
    (F4: "simpul hasil Graph Traversal sebagai anchor pencarian vektor").
    Utk tiap query baru, cari n_expansion Question tetangga (vector search)
    yang BELUM pernah muncul, lalu ambil jawaban 1-hop-nya saja (TIDAK
    traversal lebih jauh lagi -- dibatasi supaya latency tetap terkendali,
    NF3 <=15 detik).

    `edge_types` (C retrieval v3 exploratory switch, Step 4b): filters
    the 1-hop fetch types the same way traverse_graph() does. Default
    (every type) reproduces the query exactly as it always ran. If
    neither HAS_ACCEPTED_ANSWER nor HAS_ANSWER survives the filter,
    expansion can fetch nothing and returns [] immediately.

    `require_answer` (Amendment 9; default False = the expansion every run
    before it used, unchanged): per seed, fetch overfetch*n_expansion +
    |excluded| FAISS candidates, keep only Questions with >= 1 Answer not in
    exclude_answer_ids (ONE Cypher EXISTS round-trip for all seeds), and take
    the first n_expansion of them by (similarity desc, id asc) not taken by an
    earlier seed. stats gets n_expansion_requested / n_expansion_answerable."""
    edge_types = set(edge_types) if edge_types is not None else set(DEFAULT_EDGE_TYPES)
    fetch_types = [t for t in ("HAS_ACCEPTED_ANSWER", "HAS_ANSWER") if t in edge_types]
    if not traversal_candidates or not fetch_types:
        return []

    seed_questions = {}
    for c in traversal_candidates:
        qid = c["via_question_id"]
        if qid not in seed_questions:
            seed_questions[qid] = c["via_question_title"] or ""
        if len(seed_questions) >= 3:
            break

    expansion_qids = set()
    seed_of: dict = {}  # provenance: expanded question id -> (seed question id, cosine). One seed per expanded Question
    #                     (both branches exclude Questions already taken by an earlier seed).
    if require_answer:
        expansion_qids = _select_answerable_expansion(
            driver, database, seed_questions, index, ids_arr, sbert_model, n_expansion,
            already_seen_qids | exclude_question_ids, exclude_answer_ids, fetch_types, overfetch, stats, seed_of)
    else:
        for qid, title in seed_questions.items():
            q_emb = embed_query(title, sbert_model)
            found = anchor_via_vector_search(
                q_emb, index, ids_arr, top_n=n_expansion,
                exclude_ids=already_seen_qids | exclude_question_ids | expansion_qids | {qid},
                stats=stats,
            )
            expansion_qids.update(fid for fid, _ in found)
            for fid, score in found:
                seed_of[fid] = (qid, score)

    if not expansion_qids:
        return []

    exclude_a = list(exclude_answer_ids) or [-1]
    fetch_pattern = "|".join(fetch_types)
    w1, sc = (_qa_weight_cypher("r", binary_trust, vote_trust, uniform_trust), _v5_score_col(net_score_filter)) if trust_weights \
        else ("r.weight", "")
    tcol = _trust_col(trust_weights and (binary_trust or vote_trust or uniform_trust))
    candidates = []
    with driver.session(database=database) as session:
        result = session.run(
            f"""
            UNWIND $qids AS qid
            MATCH (q:Question {{id: qid}})-[r:{fetch_pattern}]->(a:Answer)
            WHERE NOT a.id IN $exclude_a
            RETURN qid AS via_question_id, q.title AS via_question_title,
                   a.id AS answer_id, a.body AS answer_body, {tcol} AS answer_trust_score,
                   a.isAccepted AS is_accepted{sc}, {w1} AS edge_weight, 'semantic' AS hop,
                   type(r) AS rel_type
            ORDER BY a.id ASC
            """,
            qids=list(expansion_qids), exclude_a=exclude_a,
        )
        for record in result:
            c = dict(record)
            seed = seed_of.get(int(c["via_question_id"]))
            c["seed_id"] = None if seed is None else int(seed[0])
            c["seed_similarity"] = None if seed is None else round(float(seed[1]), 4)
            candidates.append(c)

    if stats is not None:
        # leakage audit: expansion Questions that contributed no answer
        # (all their answers excluded, or none at all) -- counted, not acted on
        contributed = {c["via_question_id"] for c in candidates}
        stats["expansion_qids"] = sorted(expansion_qids)
        stats["expansion_qids_empty"] = sorted(expansion_qids - contributed)
    return candidates
