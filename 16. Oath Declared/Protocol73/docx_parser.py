from __future__ import annotations

from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile
from io import BytesIO
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn


MAX_ZIP_MEMBERS = 400
MAX_ZIP_UNCOMPRESSED = 32 * 1024 * 1024
MAX_ZIP_MEMBER_UNCOMPRESSED = 12 * 1024 * 1024


def _validate_docx_package(data: bytes) -> None:
    """Reject obviously abusive ZIP packages before python-docx parses them."""
    try:
        z = ZipFile(BytesIO(data))
    except BadZipFile as exc:
        raise ValueError("Invalid DOCX package") from exc
    with z:
        infos = z.infolist()
        if len(infos) > MAX_ZIP_MEMBERS:
            raise ValueError("DOCX package contains too many ZIP members")
        total = 0
        for info in infos:
            if info.flag_bits & 0x1:
                raise ValueError("Encrypted DOCX packages are not accepted")
            total += int(info.file_size)
            if info.file_size > MAX_ZIP_MEMBER_UNCOMPRESSED:
                raise ValueError("DOCX package member is too large")
            if total > MAX_ZIP_UNCOMPRESSED:
                raise ValueError("DOCX package expands beyond the allowed size")

W = {
    "br": qn("w:br"),
    "t": qn("w:t"),
    "hyperlink": qn("w:hyperlink"),
    "bookmarkStart": qn("w:bookmarkStart"),
    "numPr": qn("w:numPr"),
    "ilvl": qn("w:ilvl"),
    "numId": qn("w:numId"),
    "pStyle": qn("w:pStyle"),
    "numFmt": qn("w:numFmt"),
    "abstractNumId": qn("w:abstractNumId"),
    "startOverride": qn("w:startOverride"),
    "start": qn("w:start"),
    "instrText": qn("w:instrText"),
    "comment": qn("w:comment"),
    "vanish": qn("w:vanish"),
    "border": qn("w:pBdr"),
}


def _length_inches(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value.inches)
    except Exception:
        return None


def _line_spacing(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _alignment_name(value: Any) -> str:
    mapping = {
        WD_ALIGN_PARAGRAPH.LEFT: "left",
        WD_ALIGN_PARAGRAPH.CENTER: "center",
        WD_ALIGN_PARAGRAPH.RIGHT: "right",
        WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
    }
    return mapping.get(value, "other")


def _run_info(run) -> dict[str, Any]:
    font = run.font
    size = None
    try:
        size = float(font.size.pt) if font.size is not None else None
    except Exception:
        size = None
    hidden = bool(font.hidden)
    # Some inherited hidden runs have no Python-level flag; inspect XML too.
    rpr = run._r.rPr
    if rpr is not None and rpr.find(W["vanish"]) is not None:
        hidden = True
    underline = font.underline
    underline_name = None
    if underline is True:
        underline_name = "single"
    elif underline:
        underline_name = str(underline).split(".")[-1].lower()
    highlight = None
    try:
        highlight = str(font.highlight_color).split(".")[-1].upper() if font.highlight_color else None
    except Exception:
        highlight = None
    return {
        "text": run.text or "",
        "visible": not hidden,
        "bold": bool(font.bold),
        "italic": bool(font.italic),
        "underline": underline_name,
        "strike": bool(font.strike),
        "small_caps": bool(font.small_caps),
        "all_caps": bool(font.all_caps),
        "font_name": font.name,
        "font_size": size,
        "highlight": highlight,
    }


def _resolve_style_name(paragraph, style_cache: dict[str | None, str]) -> str:
    """Resolve a paragraph's style name, memoized by styleId for this document.

    python-docx's Styles.get_by_id()/default_for() walk every style definition in
    styles.xml (an XPath scan) on each call when a paragraph has no explicit
    w:pStyle (the common case for "default" body text), and python-docx caches
    none of this. A document body only ever uses a handful of distinct style ids
    (default body text, a heading level or two, list paragraph, ...), so resolving
    each distinct id once and reusing it turns an O(paragraphs) cost of repeated
    full-stylesheet scans into O(distinct style ids actually used).
    """
    ppr = paragraph._p.pPr
    style_el = ppr.find(W["pStyle"]) if ppr is not None else None
    style_id = style_el.get(qn("w:val")) if style_el is not None else None
    cached = style_cache.get(style_id)
    if cached is None:
        resolved = paragraph.style.name if paragraph.style else ""
        style_cache[style_id] = resolved
        return resolved
    return cached


def _paragraph_info(paragraph, style_cache: dict[str | None, str], body: bool = True) -> dict[str, Any]:
    fmt = paragraph.paragraph_format
    runs = [_run_info(r) for r in paragraph.runs]
    text = paragraph.text or ""
    ppr = paragraph._p.pPr
    numpr = ppr.find(W["numPr"]) if ppr is not None else None
    num_id = None
    ilvl = None
    if numpr is not None:
        nid = numpr.find(W["numId"])
        lev = numpr.find(W["ilvl"])
        if nid is not None:
            num_id = int(nid.get(qn("w:val")))
        if lev is not None:
            ilvl = int(lev.get(qn("w:val")))

    return {
        "text": text,
        "visible_text": "".join(r["text"] for r in runs if r["visible"]),
        "style": _resolve_style_name(paragraph, style_cache),
        "is_list": num_id is not None,
        "num_id": num_id,
        "ilvl": ilvl,
        "alignment": _alignment_name(fmt.alignment),
        "line_spacing": _line_spacing(fmt.line_spacing),
        "space_before": _length_inches(fmt.space_before),
        "space_after": _length_inches(fmt.space_after),
        "first_line_indent": _length_inches(fmt.first_line_indent),
        "left_indent": _length_inches(fmt.left_indent),
        "right_indent": _length_inches(fmt.right_indent),
        "page_break_before": bool(fmt.page_break_before),
        "runs": runs,
        "body": body,
    }


def _parse_numbering(z: ZipFile) -> dict[int, dict[str, Any]]:
    try:
        xml = z.read("word/numbering.xml")
    except KeyError:
        return {}
    from lxml import etree
    root = etree.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    abstract = {}
    for node in root.xpath("w:abstractNum", namespaces=ns):
        aid = int(node.get(qn("w:abstractNumId")))
        levels = {}
        for lvl in node.xpath("w:lvl", namespaces=ns):
            ilvl = int(lvl.get(qn("w:ilvl")))
            fmt = lvl.find("w:numFmt", namespaces=ns)
            start = lvl.find("w:start", namespaces=ns)
            levels[ilvl] = {
                "fmt": fmt.get(qn("w:val")) if fmt is not None else None,
                "start": int(start.get(qn("w:val"))) if start is not None else 1,
            }
        abstract[aid] = levels
    result = {}
    for num in root.xpath("w:num", namespaces=ns):
        nid = int(num.get(qn("w:numId")))
        aid = num.find("w:abstractNumId", namespaces=ns)
        aid_int = int(aid.get(qn("w:val"))) if aid is not None else -1
        overrides = {}
        for ov in num.xpath("w:lvlOverride", namespaces=ns):
            ilvl = int(ov.get(qn("w:ilvl")))
            so = ov.find("w:startOverride", namespaces=ns)
            if so is not None:
                overrides[ilvl] = int(so.get(qn("w:val")))
        result[nid] = {"levels": abstract.get(aid_int, {}), "overrides": overrides}
    return result


def _custom_properties(z: ZipFile) -> dict[str, str]:
    try:
        xml = z.read("docProps/custom.xml")
    except KeyError:
        return {}
    from lxml import etree
    root = etree.fromstring(xml)
    ns = {
        "cp": "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties",
        "vt": "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes",
    }
    out: dict[str, str] = {}
    for prop in root.xpath("cp:property", namespaces=ns):
        name = prop.get("name")
        vals = list(prop)
        if name and vals:
            out[name] = vals[0].text or ""
    return out


def _xml_counts(z: ZipFile) -> dict[str, Any]:
    from lxml import etree
    counts = {
        "hyperlinks": 0,
        "bookmarks": 0,
        "page_breaks": 0,
        "horizontal_borders": 0,
        "page_fields": 0,
        "numpages_fields": 0,
        "footer_page_fields": 0,
        "footer_numpages_fields": 0,
        "footnotes": 0,
        "endnotes": 0,
        "comments": 0,
        "comment_texts": [],
    }
    body_xml = z.read("word/document.xml")
    root = etree.fromstring(body_xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    counts["hyperlinks"] = len(root.xpath(".//w:hyperlink", namespaces=ns))
    counts["bookmarks"] = len(root.xpath(".//w:bookmarkStart", namespaces=ns))
    counts["page_breaks"] = len(root.xpath('.//w:br[@w:type="page"]', namespaces=ns))
    counts["horizontal_borders"] = len(root.xpath(".//w:pBdr/w:bottom", namespaces=ns))
    instr = root.xpath(".//w:instrText", namespaces=ns)
    codes = [(x.text or "").strip().upper() for x in instr]
    counts["page_fields"] = sum(1 for x in codes if x == "PAGE")
    counts["numpages_fields"] = sum(1 for x in codes if x == "NUMPAGES")

    footer_files = [n for n in z.namelist() if n.startswith("word/footer") and n.endswith(".xml")]
    footer_codes = []
    for filename in footer_files:
        try:
            fr = etree.fromstring(z.read(filename))
            footer_codes.extend((x.text or "").strip().upper() for x in fr.xpath(".//w:instrText", namespaces=ns))
        except Exception:
            continue
    counts["footer_page_fields"] = sum(1 for x in footer_codes if x == "PAGE")
    counts["footer_numpages_fields"] = sum(1 for x in footer_codes if x == "NUMPAGES")

    for filename, key in (("word/footnotes.xml", "footnotes"), ("word/endnotes.xml", "endnotes")):
        try:
            r = etree.fromstring(z.read(filename))
        except KeyError:
            continue
        nodes = r.xpath("w:footnote" if key == "footnotes" else "w:endnote", namespaces=ns)
        actual = 0
        for node in nodes:
            ident = int(node.get(qn("w:id")))
            if ident >= 0:
                actual += 1
        counts[key] = actual

    try:
        r = etree.fromstring(z.read("word/comments.xml"))
        comments = r.xpath("w:comment", namespaces=ns)
        counts["comments"] = len(comments)
        for c in comments:
            txt = "".join(c.xpath(".//w:t/text()", namespaces=ns))
            counts["comment_texts"].append(txt)
    except KeyError:
        pass
    return counts


def extract_docx(path: str | Path | bytes | bytearray) -> dict[str, Any]:
    """Parse a DOCX once from memory and reuse the same bytes for ZIP/XML inspection.

    Keeping the uploaded package in memory avoids repeated filesystem opens while
    concurrent users are submitting small DOCX files. The package is still validated
    before python-docx receives it.
    """
    if isinstance(path, (bytes, bytearray)):
        data = bytes(path)
    else:
        path_obj = Path(path)
        if path_obj.suffix.lower() != ".docx":
            raise ValueError("DOCX required")
        data = path_obj.read_bytes()

    if not data.startswith(b"PK"):
        raise ValueError("Invalid DOCX package")
    _validate_docx_package(data)
    doc = Document(BytesIO(data))
    style_cache: dict[str | None, str] = {}
    body_paragraphs = [_paragraph_info(p, style_cache) for p in doc.paragraphs]
    prose_paragraphs = [p for p in body_paragraphs if p["text"].strip() and not p["is_list"] and not p["style"].lower().startswith("heading") and p["style"].lower() not in {"title", "subtitle"}]
    list_paragraphs = [p for p in body_paragraphs if p["is_list"]]

    body_parts: list[str] = [p["visible_text"] for p in body_paragraphs if p["visible_text"]]
    table_parts: list[str] = []
    table_infos = []
    body_runs = []
    for p in body_paragraphs:
        body_runs.extend(p["runs"])
    for ti, table in enumerate(doc.tables):
        rows = []
        for row in table.rows:
            row_text = []
            for cell in row.cells:
                cell_text = "\n".join(p.text for p in cell.paragraphs)
                row_text.append(cell_text)
                table_parts.append(cell_text)
            rows.append(row_text)
        table_infos.append({"index": ti, "rows": rows, "row_count": len(rows), "col_count": len(rows[0]) if rows else 0})

    header_texts, footer_texts = [], []
    for section in doc.sections:
        header_texts.append("\n".join(p.text for p in section.header.paragraphs))
        footer_texts.append("\n".join(p.text for p in section.footer.paragraphs))

    visible_body_text = "\n".join(body_parts)
    visible_table_text = "\n".join(table_parts)
    sections = []
    for s in doc.sections:
        width = _length_inches(s.page_width)
        height = _length_inches(s.page_height)
        orientation = "landscape" if width and height and width > height else "portrait"
        sections.append({
            "page_width": width,
            "page_height": height,
            "orientation": orientation,
            "left_margin": _length_inches(s.left_margin),
            "right_margin": _length_inches(s.right_margin),
            "top_margin": _length_inches(s.top_margin),
            "bottom_margin": _length_inches(s.bottom_margin),
            "header_distance": _length_inches(s.header_distance),
            "footer_distance": _length_inches(s.footer_distance),
        })

    numbering = {}
    custom = {}
    xml_counts = {}
    with ZipFile(BytesIO(data)) as z:
        numbering = _parse_numbering(z)
        custom = _custom_properties(z)
        xml_counts = _xml_counts(z)

    core = doc.core_properties
    metadata = {
        "title": core.title or "",
        "subject": core.subject or "",
        "author": core.author or "",
        "last_modified_by": core.last_modified_by or "",
        "keywords": core.keywords or "",
        "language": core.language or "",
        "category": core.category or "",
        "comments": core.comments or "",
        "content_status": core.content_status or "",
        "identifier": core.identifier or "",
        "version": core.version or "",
        "revision": int(core.revision or 0),
        "created": core.created,
        "modified": core.modified,
        "last_printed": core.last_printed,
    }

    return {
        "text": visible_body_text,
        "table_text": visible_table_text,
        "paragraphs": [p["text"] for p in body_paragraphs],
        "body_paragraphs": body_paragraphs,
        "prose_paragraphs": prose_paragraphs,
        "list_paragraphs": list_paragraphs,
        "tables": table_infos,
        "header_texts": header_texts,
        "footer_texts": footer_texts,
        "sections": sections,
        "runs": body_runs,
        "metadata": metadata,
        "custom_properties": custom,
        "numbering": numbering,
        **xml_counts,
        "inline_images": len(doc.inline_shapes),
    }
