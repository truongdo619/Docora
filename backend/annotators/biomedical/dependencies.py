from typing import List, Dict, Any, Tuple

def kapipe_to_brat(kapipe_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert KAPIPE-formatted documents to a BRAT-like JSON structure.

    Assumptions
    ----------
    - Each sentence in `doc["sentences"]` is pre-tokenized with single spaces
      (including spaces around punctuation), like the sample you provided.
    - `mentions[i]["span"]` is (start_token, end_token) inclusive over the *whole doc*.
    - Relations in KAPIPE point to entries in doc["entities"] (i.e., coref groups).
      We connect each relation to the *first mention* of each entity group.

    Output
    ------
    A list of dicts: each has keys:
      - "text": the reconstructed paragraph text
      - "entities": list of BRAT entity entries:
            ["T#", <TYPE>, [[start_char, end_char]], "", <surface_text>]
        (end_char is exclusive)
      - "relations": list of BRAT relation entries:
            ["R#", <REL_TYPE>, [["Arg1", "T#"], ["Arg2", "T#"]]]
    """
    brat_docs = []

    for doc in kapipe_docs:
        # 1) Flatten tokens and rebuild full text (single spaces between tokens)
        sentences = doc.get("sentences", [])
        tokens: List[str] = []
        for s in sentences:
            # sentence already tokenized; split on single spaces
            tokens.extend(s.split(" ") if s else [])

        # Build text and token -> (char_start, char_end) map
        text = " ".join(tokens)
        token_char_spans: List[Tuple[int, int]] = []
        pos = 0
        for i, tok in enumerate(tokens):
            start = pos
            end = start + len(tok)
            token_char_spans.append((start, end))
            # add one space between tokens, not after the last token
            pos = end + (1 if i < len(tokens) - 1 else 0)

        # 2) Convert mentions → BRAT entities (sorted by first appearance)
        mentions = doc.get("mentions", [])
        # decorate with char spans and original index
        mention_ext = []
        for midx, m in enumerate(mentions):
            s_tok, e_tok = m["span"]
            start_char = token_char_spans[s_tok][0]
            end_char = token_char_spans[e_tok][1]  # inclusive token → exclusive char
            mention_ext.append({
                "orig_index": midx,
                "start_char": start_char,
                "end_char": end_char,
                "type": m["entity_type"].upper(),
                "surface": m.get("name", text[start_char:end_char]),
            })

        # order by first appearance (start_char), then by end to stabilize
        mention_ext.sort(key=lambda x: (x["start_char"], x["end_char"]))

        # Assign T IDs and build map from original mention index -> T#
        brat_entities = []
        mention_to_tid = {}  # orig_index -> "T#"
        for i, m in enumerate(mention_ext, start=1):
            tid = f"T{i}"
            mention_to_tid[m["orig_index"]] = tid
            brat_entities.append([
                tid,
                m["type"],
                [[m["start_char"], m["end_char"]]],
                "",
                m["surface"],
            ])

        # 3) Map KAPIPE entity groups to a representative T (first mention of the group)
        #    entity_group_to_tid: index in doc["entities"] -> "T#"
        entity_groups = doc.get("entities", [])
        entity_group_to_tid: Dict[int, str] = {}
        for gi, g in enumerate(entity_groups):
            m_indices = g.get("mention_indices", [])
            if not m_indices:
                continue  # no representative; skip (rare)
            first_m = min(m_indices)  # pick earliest by original mention index
            # Convert original mention index to its T id
            if first_m in mention_to_tid:
                entity_group_to_tid[gi] = mention_to_tid[first_m]
            else:
                # In case sorting removed it (shouldn't happen), fallback to nearest
                # but practically this path won't be used with given data
                pass

        # 4) Convert relations → BRAT relations (in input order)
        brat_relations = []
        for r_idx, r in enumerate(doc.get("relations", []), start=1):
            arg1_group = r["arg1"]
            arg2_group = r["arg2"]
            # Use the group's first-mention T id; skip if unavailable
            t1 = entity_group_to_tid.get(arg1_group)
            t2 = entity_group_to_tid.get(arg2_group)
            if not t1 or not t2:
                # If a group has no mapped T (should not happen with proper data), skip
                continue
            brat_relations.append([
                f"R{r_idx}",
                r["relation"],
                [["Arg1", t1], ["Arg2", t2]],
            ])

        brat_docs.append({
            "text": text,
            "entities": brat_entities,
            "relations": brat_relations,
        })

    return brat_docs