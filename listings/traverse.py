def traverse_graph(driver, database, anchor_ids: list, exclude_question_ids: set,
                    exclude_answer_ids: set, max_hops: int = DEFAULT_MAX_HOPS,
                    edge_types: tuple | None = None, trust_weights: bool = False, binary_trust: bool = False,
                    net_score_filter: bool = True, vote_trust: bool = False, uniform_trust: bool = False) -> list:
    """`trust_weights` (v5 only; default False = the stored edge weights, the query text of v4 unchanged): the
    answer weight is 1.0 for HAS_ACCEPTED_ANSWER and a.trustScore otherwise (also in the 2-hop product and its
    LIMIT 50 ordering), and a.score is returned as answer_score for the net-score filter.
    `binary_trust` (with trust_weights): 0.0 instead of a.trustScore, everywhere above. `net_score_filter=False`: a.score
    is not returned.

    CATATAN: traversal saat ini FIXED di 1-hop (jawaban langsung anchor)
    + 2-hop (anchor -> Question terkait -> jawabannya). Tidak digeneralisasi
    ke N-hop sembarang -- kalau nanti butuh >2 hop, tulis query tambahan
    dgn pola yang sama (JANGAN pakai variable-length path [*1..N] tanpa
    exclusion per-hop, karena leakage exclusion HARUS diterapkan di
    SETIAP node yang dilewati, bukan cuma titik akhir).

    `max_hops`/`edge_types` (C retrieval v3 exploratory switches, Step
    4b): default (2, every type below) reproduces the query exactly as
    it always ran. `max_hops=1` skips the 2-hop query entirely.
    `edge_types` filters which relationship types each query's MATCH may
    traverse -- the two 1-hop fetch types (HAS_ACCEPTED_ANSWER,
    HAS_ANSWER) and the three 2-hop relation types (IS_RELATED_TO,
    TAG_COOCCUR, EMBED_SIM) are each intersected with `edge_types`
    independently, so e.g. edge_types=("HAS_ACCEPTED_ANSWER",) alone
    disables HAS_ANSWER's 1-hop fetch AND (having no 2-hop relation
    types left) the entire 2-hop query.
    """
    edge_types = set(edge_types) if edge_types is not None else set(DEFAULT_EDGE_TYPES)
    fetch_types = [t for t in ("HAS_ACCEPTED_ANSWER", "HAS_ANSWER") if t in edge_types]
    relation_types = [t for t in ("IS_RELATED_TO", "TAG_COOCCUR", "EMBED_SIM") if t in edge_types]

    exclude_q = list(exclude_question_ids) or [-1]
    exclude_a = list(exclude_answer_ids) or [-1]

    candidates = []
    if not fetch_types:
        return candidates

    fetch_pattern = "|".join(fetch_types)
    w1, w3, sc = (_qa_weight_cypher("r", binary_trust, vote_trust, uniform_trust), _qa_weight_cypher("r3", binary_trust, vote_trust, uniform_trust),
                  _v5_score_col(net_score_filter)) if trust_weights else ("r.weight", "r3.weight", "")
    tcol = _trust_col(trust_weights and (binary_trust or vote_trust or uniform_trust))
    with driver.session(database=database) as session:
        # 1-hop: jawaban langsung milik anchor
        result = session.run(
            f"""
            UNWIND $anchor_ids AS anchor_id
            MATCH (anchor:Question {{id: anchor_id}})-[r:{fetch_pattern}]->(a:Answer)
            WHERE NOT a.id IN $exclude_a
            RETURN anchor_id AS via_question_id, anchor.title AS via_question_title,
                   a.id AS answer_id, a.body AS answer_body, {tcol} AS answer_trust_score,
                   a.isAccepted AS is_accepted{sc}, {w1} AS edge_weight, 1 AS hop,
                   type(r) AS rel_type
            ORDER BY a.id ASC
            """,
            anchor_ids=anchor_ids, exclude_a=exclude_a,
        )
        for record in result:
            c = dict(record)
            c["anchor_id"] = c["via_question_id"]  # provenance: a 1-hop item's anchor IS its via_question
            candidates.append(c)

        # 2-hop: anchor -> Question terkait (IS_RELATED_TO/TAG_COOCCUR/EMBED_SIM)
        # -> jawaban Question terkait tsb. EXCLUDE eval question sbg Question
        # terkait (leakage prevention #2) DAN exclude jawabannya.
        if max_hops >= 2 and relation_types:
            relation_pattern = "|".join(relation_types)
            result = session.run(
                f"""
                UNWIND $anchor_ids AS anchor_id
                MATCH (anchor:Question {{id: anchor_id}})-[r2:{relation_pattern}]->(q2:Question)
                WHERE NOT q2.id IN $exclude_q
                MATCH (q2)-[r3:{fetch_pattern}]->(a:Answer)
                WHERE NOT a.id IN $exclude_a
                WITH anchor_id, q2, a, r2, r3, (r2.weight * {w3}) AS edge_weight
                ORDER BY edge_weight DESC, a.id ASC
                LIMIT 50
                RETURN q2.id AS via_question_id, q2.title AS via_question_title,
                       a.id AS answer_id, a.body AS answer_body, {tcol} AS answer_trust_score,
                       a.isAccepted AS is_accepted{sc}, edge_weight, 2 AS hop,
                       (type(r2) + '->' + type(r3)) AS rel_type,
                       anchor_id
                """,
                anchor_ids=anchor_ids, exclude_q=exclude_q, exclude_a=exclude_a,
            )
            candidates.extend(dict(record) for record in result)

    return candidates
