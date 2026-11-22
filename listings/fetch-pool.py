def fetch_answer_pool(driver, database, answer_ids: list, exclude_question_ids: set, exclude_answer_ids: set,
                      binary_trust: bool = False, net_score_filter: bool = True, vote_trust: bool = False, uniform_trust: bool = False) -> list:
    """v5: the candidates for B's top answers, shaped like traverse_graph()'s 1-hop rows (the answer's own question
    is its via question and anchor; w_qq' = 1, so edge_weight is the answer weight alone). The exclusion is applied
    again in the query, on top of the one the answer search already applied. `binary_trust`/`net_score_filter`: as in
    traverse_graph()."""
    if not answer_ids:
        return []
    tcol = _trust_col(binary_trust or vote_trust or uniform_trust)
    with driver.session(database=database) as session:
        result = session.run(
            f"""
            MATCH (q:Question)-[r:HAS_ACCEPTED_ANSWER|HAS_ANSWER]->(a:Answer)
            WHERE a.id IN $answer_ids AND NOT a.id IN $exclude_a AND NOT q.id IN $exclude_q
            RETURN q.id AS via_question_id, q.title AS via_question_title,
                   a.id AS answer_id, a.body AS answer_body, {tcol} AS answer_trust_score,
                   a.isAccepted AS is_accepted{_v5_score_col(net_score_filter)},
                   {_qa_weight_cypher("r", binary_trust, vote_trust, uniform_trust)} AS edge_weight, 1 AS hop,
                   type(r) AS rel_type
            ORDER BY a.id ASC
            """,
            answer_ids=[int(a) for a in answer_ids], exclude_a=list(exclude_answer_ids) or [-1],
            exclude_q=list(exclude_question_ids) or [-1],
        )
        out = []
        for record in result:
            c = dict(record)
            c["anchor_id"] = c["via_question_id"]
            out.append(c)
    return out
