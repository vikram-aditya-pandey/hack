import fitz  # PyMuPDF
import sys
import json
from collections import defaultdict


def load_pdf(path):
    doc = fitz.open(path)
    pages = []
    for i, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]
        spans = []
        for b in blocks:
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    if s["text"].strip():
                        spans.append({
                            "text": s["text"].strip(),
                            "size": round(s["size"], 1),
                            "font": s["font"],
                            "y": round(s["origin"][1], 1),
                            "x": round(s["origin"][0], 1),
                            "page": i
                        })
        pages.append(spans)
    return pages


def group_by_size(spans):
    grouped = defaultdict(list)
    for span in spans:
        key = (span["size"], span["font"])
        grouped[key].append(span)
    return grouped


def detect_heading_sizes(grouped):
    counts = {k: len(v) for k, v in grouped.items()}
    sorted_keys = sorted(counts.items(), key=lambda x: (-x[0][0], -x[1]))  # Prefer large sizes
    top_styles = [k for k, _ in sorted_keys[:6]]
    return {style: f"H{i+1}" for i, style in enumerate(sorted(top_styles, key=lambda s: -s[0]))}


def reconstruct_lines(spans):
    lines = defaultdict(list)
    for s in spans:
        key = (s["page"], s["y"])
        lines[key].append(s)

    line_objs = []
    for (page, y), items in lines.items():
        items.sort(key=lambda x: x["x"])
        text = " ".join([s["text"] for s in items])
        size = max(s["size"] for s in items)
        font = items[0]["font"]
        line_objs.append({
            "text": text,
            "size": size,
            "font": font,
            "y": y,
            "page": page
        })
    return line_objs


def extract_headings(lines, heading_map):
    headings = []
    for line in lines:
        key = (line["size"], line["font"])
        if key in heading_map:
            level = heading_map[key]
            headings.append({
                "level": level,
                "text": line["text"],
                "page": line["page"]
            })
    return headings


def extract_title(headings):
    h1s = [h["text"] for h in headings if h["level"] == "H1" and h["page"] <= 1]
    return " ".join(h1s).strip() if h1s else "Untitled Document"


def main(pdf_path):
    print("📄 Parsing PDF...")
    pages = load_pdf(pdf_path)

    # 🔧 Flatten all spans into one list
    all_spans = [span for page in pages for span in page]

    grouped = group_by_size(all_spans)
    heading_map = detect_heading_sizes(grouped)
    lines = reconstruct_lines(all_spans)
    headings = extract_headings(lines, heading_map)
    title = extract_title(headings)

    result = {
        "title": title,
        "outline": headings
    }

    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("\n✅ Extraction complete. Output saved to result.json")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_headings.py <pdf-file>")
    else:
        main(sys.argv[1])
