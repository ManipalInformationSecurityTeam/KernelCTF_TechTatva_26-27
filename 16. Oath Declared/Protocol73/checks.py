from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import re
from math import isclose

from requirements import REQUIREMENTS, Requirement

REQUIREMENT_BY_ID = {r.id: r for r in REQUIREMENTS}


def normalize_text(text: str) -> str:
    return (
        (text or "")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\xa0", " ")
        .replace("\u2028", "\n")
        .replace("\u2029", "\n")
    )


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*|\d+", normalize_text(text))


def lower_words(text: str) -> list[str]:
    return [w.casefold() for w in words(text)]


def sentences(text: str) -> list[str]:
    t = normalize_text(text).strip()
    if not t:
        return []
    parts = re.split(r"(?<=[.!?])\s+", t)
    return [p.strip() for p in parts if p.strip()]


def standalone(text: str, token: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])", text or "", re.I) is not None


def exact_phrase(text: str, phrase: str) -> bool:
    return phrase.casefold() in (text or "").casefold()


def approximately(a: float | None, b: float, eps: float = 0.01) -> bool:
    return a is not None and isclose(a, b, abs_tol=eps)


def parse_answer_present(text: str, answer: str) -> bool:
    if re.fullmatch(r"[A-Za-z0-9]+(?:[ .'-][A-Za-z0-9]+)*", answer):
        if " " in answer or "-" in answer or "'" in answer or "." in answer:
            return answer.casefold() in text.casefold()
        return standalone(text, answer)
    return exact_phrase(text, answer)


def contiguous_list_groups(paragraphs, numbering):
    groups = []
    current = None
    for idx, p in enumerate(paragraphs):
        if not p["is_list"]:
            if current:
                groups.append(current)
                current = None
            continue
        num_id = p["num_id"]
        info = numbering.get(num_id, {})
        level = p.get("ilvl", 0)
        lvl = info.get("levels", {}).get(level, {})
        fmt = lvl.get("fmt")
        key = (num_id, level, fmt)
        if current and current["key"] == key and idx == current["last_index"] + 1:
            current["items"].append(p)
            current["last_index"] = idx
        else:
            if current:
                groups.append(current)
            current = {"key": key, "items": [p], "last_index": idx}
    if current:
        groups.append(current)
    return groups


def numbered_values(group, numbering):
    num_id, level, fmt = group["key"]
    info = numbering.get(num_id, {})
    override_start = info.get("overrides", {}).get(level)
    base_start = info.get("levels", {}).get(level, {}).get("start", 1)
    start = override_start if override_start is not None else base_start
    return list(range(start, start + len(group["items"])))


def check_requirement(req_id: str, parsed: dict) -> bool:
    req: Requirement = REQUIREMENT_BY_ID[req_id]
    text = normalize_text(parsed.get("text", ""))
    ltext = text.casefold()
    toks = lower_words(text)
    sents = sentences(text)
    prose = parsed.get("prose_paragraphs", [])
    visible_runs = [r for r in parsed.get("runs", []) if r.get("visible")]
    all_runs = parsed.get("runs", [])
    sections = parsed.get("sections", [])
    metadata = parsed.get("metadata", {})
    custom = parsed.get("custom_properties", {})

    k, v = req.kind, req.value

    if k == "min_words":
        return len(toks) >= int(v)
    if k == "min_chars_no_ws":
        return len(re.sub(r"\s+", "", text)) >= int(v)
    if k == "exact_prose_paragraphs":
        return len([p for p in prose if p["visible_text"].strip()]) == int(v)
    if k == "first_prose_words_range":
        if not prose:
            return False
        lo, hi = v
        return lo <= len(words(prose[0]["visible_text"])) <= hi
    if k == "sentence_exact_words":
        return any(len(words(s)) == int(v) for s in sents)
    if k == "sentence_words_range":
        lo, hi = v
        return any(lo <= len(words(s)) <= hi for s in sents)
    if k == "sentence_min_words":
        return any(len(words(s)) >= int(v) for s in sents)
    if k == "sentence_max_words":
        return any(0 < len(words(s)) <= int(v) for s in sents)
    if k == "contains":
        return exact_phrase(text, str(v))
    if k == "word_exact_count":
        word, count = v
        return toks.count(str(word).casefold()) == int(count)
    if k == "forbid_chars":
        return bool(text.strip()) and not any(ch in text for ch in str(v))
    if k == "word_at_least":
        word, count = v
        return toks.count(str(word).casefold()) >= int(count)
    if k == "phrase_exact_count":
        phrase, count = v
        return ltext.count(str(phrase).casefold()) == int(count)
    if k == "singleton_words":
        return sum(1 for c in Counter(toks).values() if c == 1) >= int(v)
    if k == "longest_word_min":
        return any(len(re.sub(r"[^A-Za-z]", "", w)) >= int(v) for w in words(text))
    if k == "sentence_punct_exact":
        char, count = v
        return any(s.count(char) == int(count) for s in sents)
    if k == "sentence_ends":
        return any(s.endswith(str(v)) for s in sents)
    if k == "char_exact_count":
        char, count = v
        return text.count(char) == int(count)
    if k == "regex_exact_count":
        pattern, count = v
        return len(re.findall(pattern, text, flags=re.I)) == int(count)
    if k == "first_word":
        return bool(toks) and toks[0] == str(v).casefold()
    if k == "last_word":
        return bool(toks) and toks[-1] == str(v).casefold()
    if k == "three_four_letter_words":
        alpha = re.findall(r"[A-Za-z]+", text)
        return any(all(len(w) == 4 for w in alpha[i:i+3]) for i in range(max(0, len(alpha)-2)))
    if k == "has_hyphenated_word":
        return re.search(r"\b[A-Za-z]{2,}-[A-Za-z]{2,}\b", text) is not None
    if k == "sentence_all_vowels":
        return any(all(ch in s.casefold() for ch in "aeiou") for s in sents)
    if k == "sentence_parentheses_once":
        return any(s.count("(") == 1 and s.count(")") == 1 for s in sents)
    if k == "standalone_number":
        return standalone(text, str(v))

    if k == "section_page_size":
        idx, expected = v
        if len(sections) <= idx:
            return False
        w = sections[idx]["page_width"]
        h = sections[idx]["page_height"]
        if expected == "A4":
            return approximately(w, 8.27) and approximately(h, 11.69)
        if expected == "LETTER":
            return approximately(w, 8.50) and approximately(h, 11.00)
        return False
    if k == "section_orientation":
        idx, expected = v
        return len(sections) > idx and sections[idx]["orientation"] == expected
    if k == "all_margins":
        x = float(v)
        return bool(sections) and all(all(approximately(s[key], x) for key in ("left_margin","right_margin","top_margin","bottom_margin")) for s in sections)
    if k == "all_header_distance":
        return bool(sections) and all(approximately(s["header_distance"], float(v)) for s in sections)
    if k == "all_footer_distance":
        return bool(sections) and all(approximately(s["footer_distance"], float(v)) for s in sections)
    if k == "all_prose_line_spacing":
        return bool(prose) and all(approximately(p["line_spacing"], float(v)) for p in prose)
    if k == "alignment_exact_count":
        align, count = v
        return sum(1 for p in prose if p["alignment"] == align) == int(count)
    if k == "space_before_any":
        return any(approximately(p["space_before"], float(v) / 72.0, 0.005) for p in prose)
    if k == "space_after_any":
        return any(approximately(p["space_after"], float(v) / 72.0, 0.005) for p in prose)
    if k == "first_line_indent_any":
        return any(approximately(p["first_line_indent"], float(v)) for p in prose)
    if k == "left_indent_any":
        return any(approximately(p["left_indent"], float(v)) for p in prose)
    if k == "heading_exact":
        style, expected = v
        return any(p["style"] == style and p["text"].strip() == expected for p in parsed.get("body_paragraphs", []))
    if k == "heading_run_style":
        style, bold, size = v
        for p in parsed.get("body_paragraphs", []):
            if p["style"] == style:
                return any(r["visible"] and r["bold"] == bold and approximately(r["font_size"], float(size), 0.01) for r in p["runs"])
        return False
    if k == "run_font":
        name, size = v
        return any(r["visible"] and r["font_name"] and r["font_name"].casefold() == str(name).casefold() and approximately(r["font_size"], float(size), 0.01) for r in visible_runs)
    if k == "run_combo_biu":
        return any(r["visible"] and r["bold"] and r["italic"] and r["underline"] not in (None, "none") for r in visible_runs)
    if k == "run_highlight_exact":
        return sum(1 for r in visible_runs if r["highlight"] in ("YELLOW", "WD_COLOR_INDEX.YELLOW")) == 1
    if k == "run_strike_exact":
        return sum(1 for r in visible_runs if r["strike"]) == int(v)
    if k == "run_double_underline_exact":
        return sum(1 for r in visible_runs if r["underline"] and "double" in r["underline"]) == int(v)
    if k == "run_smallcaps_exact":
        return sum(1 for r in visible_runs if r["small_caps"]) == int(v)
    if k == "run_hidden_exact":
        return sum(1 for r in all_runs if not r["visible"]) == int(v)
    if k == "inline_images_exact":
        return int(parsed.get("inline_images", 0)) == int(v)
    if k == "table_exact_shape":
        count, rows, cols = v
        tables = parsed.get("tables", [])
        return len(tables) == count and any(t["row_count"] == rows and t["col_count"] == cols for t in tables)
    if k == "table_cell_exact":
        ti, ri, ci, expected = v
        tables = parsed.get("tables", [])
        if len(tables) <= ti or len(tables[ti]["rows"]) <= ri or len(tables[ti]["rows"][ri]) <= ci:
            return False
        return tables[ti]["rows"][ri][ci].strip().casefold() == str(expected).casefold()
    if k == "bullet_list":
        groups = contiguous_list_groups(parsed.get("body_paragraphs", []), parsed.get("numbering", {}))
        bullet_groups = [g for g in groups if g["key"][2] in ("bullet", "symbol")]
        return len(bullet_groups) == 1 and len(bullet_groups[0]["items"]) == int(v)
    if k == "numbered_list":
        groups = contiguous_list_groups(parsed.get("body_paragraphs", []), parsed.get("numbering", {}))
        nums = []
        for g in groups:
            if g["key"][2] in ("decimal", "decimalZero"):
                nums.append(numbered_values(g, parsed.get("numbering", {})))
        return len(nums) == 1 and nums[0] == list(v)
    if k == "hyperlink_exact":
        return parsed.get("hyperlinks", 0) == int(v)
    if k == "bookmark_exact":
        return parsed.get("bookmarks", 0) == int(v)
    if k == "page_break_exact":
        return parsed.get("page_breaks", 0) == int(v)
    if k == "section_count":
        return len(sections) == int(v)
    if k == "header_exact":
        expected = str(v).casefold()
        return bool(parsed.get("header_texts")) and all(h.strip().casefold() == expected for h in parsed.get("header_texts", []))
    if k == "footer_contains":
        expected = str(v).casefold()
        return bool(parsed.get("footer_texts")) and all(expected in f.casefold() for f in parsed.get("footer_texts", []))
    if k == "field_exact":
        field, count = v
        key = "footer_page_fields" if field == "PAGE" else "footer_numpages_fields"
        return parsed.get(key, 0) == int(count)
    if k == "footnote_exact":
        return parsed.get("footnotes", 0) == int(v)
    if k == "endnote_exact":
        return parsed.get("endnotes", 0) == int(v)
    if k == "comment_exact":
        return parsed.get("comments", 0) == int(v)
    if k == "comment_text_exact":
        texts = parsed.get("comment_texts", [])
        return len(texts) == 1 and texts[0].casefold() == str(v).casefold()
    if k == "meta_contains":
        field, needle = v
        return str(needle).casefold() in str(metadata.get(field, "")).casefold()
    if k == "meta_exact":
        field, expected = v
        return str(metadata.get(field, "")).casefold() == str(expected).casefold()
    if k == "meta_keyword":
        return str(v).casefold() in str(metadata.get("keywords", "")).casefold().replace(";", " ").replace(",", " ").split()
    if k == "meta_int":
        field, expected = v
        try:
            return int(metadata.get(field, 0)) == int(expected)
        except Exception:
            return False
    if k == "meta_before":
        field, iso = v
        value = metadata.get(field)
        if not value:
            return False
        cutoff = datetime.fromisoformat(iso)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc) < cutoff
    if k == "meta_date_exact":
        field, expected_date = v
        value = metadata.get(field)
        if not value:
            return False
        try:
            return value.date().isoformat() == str(expected_date)
        except Exception:
            return False
    if k == "meta_present":
        return bool(metadata.get(v))
    if k == "custom_prop_exact":
        name, expected = v
        return str(custom.get(name, "")).casefold() == str(expected).casefold()
    if k == "trivia":
        return parse_answer_present(text, str(v))

    raise KeyError(f"Unknown requirement kind: {k}")
