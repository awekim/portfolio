# bib2json.py
# python bib2json.py publication.bib publications.json
import re, json, sys

src = sys.argv[1] if len(sys.argv)>1 else "publication.bib"
dst = sys.argv[2] if len(sys.argv)>2 else "publication.json"

def split_entries(text: str):
    out, i, n = [], 0, len(text)
    while i < n:
        at = text.find("@", i)
        if at == -1: break
        m = re.match(r"@([A-Za-z]+)\s*\{", text[at:])
        if not m: i = at+1; continue
        brace_pos = at + text[at:].find("{")
        depth, j, end = 0, brace_pos, None
        while j < n:
            ch = text[j]
            if ch == "{": depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0: end = j+1; break
            j += 1
        out.append(text[at:(end or n)].strip())
        i = end or n
    return out

def parse_entry(e: str):
    m = re.match(r"@([A-Za-z]+)\s*\{\s*([^,]*)\s*,", e, re.DOTALL)
    etype = (m.group(1).strip().lower() if m else "misc")
    start = e.find("{"); body = e[start+1:]; 
    if body.endswith("}"): body = body[:-1]
    fields, cur, depth, inq = {}, [], 0, False
    for ch in body:
        if ch == '"': inq = not inq; cur.append(ch)
        elif ch == "{": depth += 1; cur.append(ch)
        elif ch == "}": depth = max(0, depth-1); cur.append(ch)
        elif ch == "," and depth == 0 and not inq:
            seg = "".join(cur).strip()
            if "=" in seg:
                k,v = seg.split("=",1)
                fields[k.strip().lower()] = v.strip().strip(",").strip()
            cur = []
        else: cur.append(ch)
    seg = "".join(cur).strip()
    if seg and "=" in seg:
        k,v = seg.split("=",1)
        fields[k.strip().lower()] = v.strip().strip(",").strip()

    def clean(v):
        v = v.strip()
        if v.startswith("{") and v.endswith("}"): v = v[1:-1].strip()
        if v.startswith('"') and v.endswith('"'): v = v[1:-1].strip()
        return re.sub(r"\s+", " ", v)

    fields = {k: clean(v) for k,v in fields.items()}

    def mapType(t):
        t = etype.lower()
        if t == "article": return "journal"
        if t in ("inproceedings","conference","proceedings"): return "conference"
        if t in ("techreport","phdthesis","mastersthesis"): return "report"
        return "working"

    try:
        year = int(re.findall(r"\d{4}", fields.get("year",""))[0])
    except: year = None

    def fmt_authors(raw):
        if not raw: return ""
        parts = re.split(r"\s+and\s+", raw, flags=re.IGNORECASE)
        out = []
        for n in parts:
            n = n.strip()
            if "," in n:
                last, rest = n.split(",",1)
                initials = " ".join([p.strip()[0].upper()+"." for p in rest.strip().split() if p.strip()])
                out.append((last.strip() + " " + initials).strip())
            else:
                out.append(n)
        return ", ".join(out)

    url = fields.get("url","")
    doi = fields.get("doi","")
    link = url if url else (f"https://doi.org/{doi}" if doi else "")

    keywords = []
    if fields.get("keywords"):
        keywords = [k.strip() for k in re.split(r"[;,]", fields["keywords"]) if k.strip()]

    return {
        "type": mapType(etype),
        "year": year,
        "title": fields.get("title",""),
        "authors": fmt_authors(fields.get("author","")),
        "venue": fields.get("journal") or fields.get("booktitle") or fields.get("institution") or "",
        "link": link,
        "keywords": keywords,
        "bibtex": e
    }

text = open(src, encoding="utf-8").read()
items = [parse_entry(e) for e in split_entries(text)]
with open(dst, "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
print(f"OK: {dst} ({len(items)} items)")
