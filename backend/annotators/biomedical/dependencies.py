
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

        normalized_doc, _ = fix_misaligned_entities({
            "text": text,
            "entities": brat_entities,
            "relations": brat_relations,
        })
        brat_docs.append(normalized_doc)
    
    return brat_docs


import re
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional
from difflib import SequenceMatcher

@dataclass
class FixReport:
    tid: str
    old_spans: List[Tuple[int, int]]
    new_spans: List[Tuple[int, int]]
    reason: str

_PUNCT_EDGES = r""" \t\r\n.,;:!?)]}'"“”’\""""

def _strip_edge_punct(s: str) -> str:
    return s.strip(_PUNCT_EDGES)

def _normalize_spaces(s: str) -> str:
    return re.sub(r'\s+', ' ', s)

def _hyphen_tolerant_pattern(token: str) -> str:
    """
    Build a regex that tolerates hyphenation inside words:
    'cancer' -> c-?a-?n-?c-?e-?r (case-insensitive)
    Keeps non-letters as literals (escaped).
    """
    parts = []
    for ch in token:
        if ch.isalpha():
            parts.append(re.escape(ch) + r"-?")
        else:
            parts.append(re.escape(ch))
    return "".join(parts)

def _build_hyphen_tolerant_regex(phrase: str) -> re.Pattern:
    # Split on whitespace to allow \s+ between words, but allow hyphens inside words.
    words = _normalize_spaces(phrase).strip().split(" ")
    word_patterns = [_hyphen_tolerant_pattern(w) for w in words if w]
    pattern = r"\b" + r"\s+".join(word_patterns) + r"\b"
    return re.compile(pattern, flags=re.IGNORECASE)

def _find_best_exact_span(doc: str, needle: str, around: Optional[int], window: int) -> Optional[Tuple[int,int,str]]:
    """
    Try several exact-ish searches:
    1) raw needle
    2) edge-punct stripped
    3) hyphen-tolerant regex
    Search priority favors occurrences *near* `around`.
    """
    candidates: List[Tuple[int,int,str]] = []

    def add_all_occurrences(pattern: re.Pattern, label: str):
        for m in pattern.finditer(doc):
            candidates.append((m.start(), m.end(), label))

    # Limit to a window around the original start to avoid picking far duplicates.
    L = 0 if around is None else max(0, around - window)
    R = len(doc) if around is None else min(len(doc), around + window)

    sub = doc[L:R]

    # 1) Raw needle, case-insensitive
    if needle:
        raw = re.compile(re.escape(needle), re.IGNORECASE)
        add_all_occurrences(raw, "exact")
        # 2) Stripped edges
        stripped = _strip_edge_punct(needle)
        if stripped and stripped.lower() != needle.lower():
            add_all_occurrences(re.compile(re.escape(stripped), re.IGNORECASE), "edge-stripped")
        # 3) Hyphen-tolerant
        ht = _build_hyphen_tolerant_regex(stripped or needle)
        for m in ht.finditer(sub):
            # map back to absolute
            candidates.append((L + m.start(), L + m.end(), "hyphen-tolerant"))

    # Rank by distance to `around`
    if not candidates:
        return None
    if around is None:
        return min(candidates, key=lambda t: t[0])
    return min(candidates, key=lambda t: abs(t[0] - around))

def _approx_span(doc: str, needle: str, around: Optional[int], window: int, min_ratio: float=0.80) -> Optional[Tuple[int,int]]:
    """
    Approximate search in a window using difflib, for last-resort fixing.
    """
    if not needle:
        return None
    target = _normalize_spaces(_strip_edge_punct(needle))
    if not target:
        return None
    L = 0 if around is None else max(0, around - window)
    R = len(doc) if around is None else min(len(doc), around + window)
    sub = doc[L:R]

    best = (None, 0.0, None)  # (span, ratio, text)
    tlen = len(target)
    # Slide a window roughly around the same length ± 40%
    min_len = max(1, int(tlen * 0.6))
    max_len = min(len(sub), int(tlen * 1.4))

    for start in range(0, max(0, len(sub)-min_len+1), max(1, tlen // 4)):
        for end in (start + tlen, start + min_len, start + max_len):
            end = min(len(sub), end)
            if end <= start: 
                continue
            chunk = sub[start:end]
            ratio = SequenceMatcher(None, target.lower(), chunk.lower()).ratio()
            if ratio > best[1]:
                best = ((L + start, L + end), ratio, chunk)
    if best[0] and best[1] >= min_ratio:
        return best[0]
    return None

def fix_misaligned_entities(obj: Dict[str, Any], window: int = 120) -> Tuple[Dict[str, Any], List[FixReport]]:
    """
    Input format:
      obj = {
        "text": <str>,
        "entities": [
            [tid, type, [[start, end], ...], "", surface_text],
            ...
        ],
        "relations": [...]
      }

    Returns:
      (new_obj, reports) with corrected spans (in-place content preserved).
    """
    doc = obj["text"]
    entities = obj["entities"]
    new_entities = []
    reports: List[FixReport] = []

    for ent in entities:
        tid, etype, span_list, meta, surface = ent
        fixed_spans: List[Tuple[int,int]] = []
        changed = False
        reasons = []

        for (start, end) in span_list:
            # Guard invalid ranges
            if start is None or end is None or start < 0 or end > len(doc) or end <= start:
                around = start if isinstance(start, int) else None
                best = _find_best_exact_span(doc, surface, around, window) \
                    or ( _approx_span(doc, surface, around, window) and (_approx_span(doc, surface, around, window)[0], _approx_span(doc, surface, around, window)[1], "approx") )
                if best:
                    if isinstance(best, tuple) and len(best)==3:
                        ns, ne, lbl = best
                    else:
                        ns, ne = best
                        lbl = "approx"
                    fixed_spans.append((ns, ne))
                    changed = True
                    reasons.append(f"invalid -> {lbl}")
                else:
                    # keep as-is if truly unrecoverable
                    fixed_spans.append((start, end))
                    reasons.append("invalid-unfixed")
                continue

            slice_text = doc[start:end]
            if slice_text == surface:
                fixed_spans.append((start, end))
                continue

            # Quick tolerant checks: case-insensitive, edge punctuation
            if slice_text.lower() == surface.lower():
                fixed_spans.append((start, end))
                continue
            if _strip_edge_punct(slice_text).lower() == _strip_edge_punct(surface).lower():
                # Keep original if only punctuation differs (spans still valid)
                fixed_spans.append((start, end))
                continue

            # Try to re-locate near the original
            best = _find_best_exact_span(doc, surface, start, window)
            if best:
                ns, ne, lbl = best
                fixed_spans.append((ns, ne))
                changed = True
                reasons.append(f"mismatch -> {lbl}")
            else:
                approx = _approx_span(doc, surface, start, window)
                if approx:
                    ns, ne = approx
                    fixed_spans.append((ns, ne))
                    changed = True
                    reasons.append("mismatch -> approx")
                else:
                    # give up, keep original
                    fixed_spans.append((start, end))
                    reasons.append("mismatch-unfixed")

        if changed:
            reports.append(FixReport(tid=tid, old_spans=[tuple(x) for x in span_list], new_spans=fixed_spans, reason="; ".join(sorted(set(reasons)))))
        # Replace span list
        new_entities.append([tid, etype, [list(x) for x in fixed_spans], meta, surface])

    new_obj = dict(obj)
    new_obj["entities"] = new_entities
    return new_obj, reports