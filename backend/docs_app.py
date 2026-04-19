from html import unescape
from pathlib import Path
import re

import markdown
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="MakerPi GroundControl Docs",
    description="Documentation site for MakerPi GroundControl",
    version="0.1.0",
)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _sort_key(path: Path):
    match = re.match(r"^(\d+)-", path.stem)
    if match:
        return (0, int(match.group(1)), path.name.lower())
    return (1, 9999, path.name.lower())


def _clean_slug(stem: str) -> str:
    return re.sub(r"^\d+-", "", stem)


def _humanize_slug(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").title()


def _extract_title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return _humanize_slug(_clean_slug(path.stem))


def _discover_docs():
    files = sorted(DOCS_DIR.glob("*.md"), key=_sort_key)
    
    # Group files by their base slug (without language suffix)
    files_by_slug = {}
    for file_path in files:
        stem = file_path.stem
        if stem.endswith(".en"):
            base_slug = stem[:-3]  # Remove .en
        elif stem.endswith(".de"):
            base_slug = stem[:-3]  # Remove .de
        else:
            base_slug = stem  # No suffix
        
        if base_slug not in files_by_slug:
            files_by_slug[base_slug] = {}
        
        if stem.endswith(".en"):
            files_by_slug[base_slug]["en"] = file_path
        elif stem.endswith(".de"):
            files_by_slug[base_slug]["de"] = file_path
        else:
            files_by_slug[base_slug]["base"] = file_path
    
    docs = []
    for base_slug, lang_files in sorted(files_by_slug.items(), key=lambda x: _sort_key(Path(x[0] + ".md"))):
        # Priority: .de.md > base.md (treat as German) > .en.md (fallback)
        if "de" in lang_files:
            file_path = lang_files["de"]
        elif "base" in lang_files:
            file_path = lang_files["base"]
        else:
            # Only English available - use it as fallback
            file_path = lang_files["en"]
        
        slug = _clean_slug(base_slug)
        docs.append({
            "slug": slug,
            "title": _extract_title(file_path),
            "path": file_path,
            "base_filename": base_slug,  # e.g., "00-overview" without language suffix
            "has_english": "en" in lang_files,
        })
    return docs


def _get_doc_path(slug: str, lang: str = "de", docs: list = None) -> Path | None:
    """Get the appropriate file path for a doc slug and language"""
    # Find the doc entry to get the base_filename
    if docs is None:
        docs = _discover_docs()
    
    base_filename = None
    for doc in docs:
        if doc["slug"] == slug:
            base_filename = doc["base_filename"]
            break
    
    if not base_filename:
        # Fallback: try to construct from slug
        base_filename = slug
    
    if lang == "en":
        # Look for .en.md version first
        en_path = DOCS_DIR / f"{base_filename}.en.md"
        if en_path.exists():
            return en_path
    
    # Try .de.md version (German)
    de_path = DOCS_DIR / f"{base_filename}.de.md"
    if de_path.exists():
        return de_path
    
    # Fall back to base file (for README, etc.)
    base_path = DOCS_DIR / f"{base_filename}.md"
    if base_path.exists() and not base_path.stem.endswith(".en"):
        return base_path
    
    return None


def _normalize_slug(slug: str) -> str:
    normalized = slug.strip().strip("/")
    if normalized.endswith(".md"):
        normalized = normalized[:-3]
    normalized = Path(normalized).stem
    return _clean_slug(normalized)


def _render_markdown(path: Path):
    md = markdown.Markdown(
        extensions=["toc", "tables", "fenced_code", "attr_list", "sane_lists"],
        extension_configs={"toc": {"permalink": False}},
    )
    source = path.read_text(encoding="utf-8")
    html_content = md.convert(source)
    # Convert fenced mermaid blocks to .mermaid divs so Mermaid.js can render them
    # The markdown library HTML-escapes code block content, so we unescape it first
    def _mermaid_div(m: re.Match) -> str:
        return f'<div class="mermaid">{unescape(m.group(1))}</div>'
    html_content = re.sub(
        r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        _mermaid_div,
        html_content,
        flags=re.DOTALL,
    )
    return html_content, md.toc


def _docs_base_url(request: Request) -> str:
    hostname = request.url.hostname or "localhost"
    return f"{request.url.scheme}://{hostname}:8000"


@app.get("/health")
async def health():
    return {"ok": True, "docs_count": len(_discover_docs())}


@app.get("/api/search")
async def search_docs(q: str = ""):
    q = q.strip().lower()
    if not q or len(q) < 2:
        return {"results": []}
    results = []
    for doc in _discover_docs():
        text = doc["path"].read_text(encoding="utf-8")
        text_lower = text.lower()
        if q in text_lower:
            pos = text_lower.find(q)
            start = max(0, pos - 60)
            excerpt = text[start: pos + 120].replace("\n", " ").strip()
            if start > 0:
                excerpt = "…" + excerpt
            results.append({"slug": doc["slug"], "title": doc["title"], "excerpt": excerpt})
    return {"results": results[:12]}


@app.get("/", response_class=HTMLResponse)
async def docs_index():
    docs = _discover_docs()
    if not docs:
        raise HTTPException(status_code=404, detail="No documentation pages found")
    return RedirectResponse(url=f"/page/{docs[0]['slug']}", status_code=307)


@app.get("/page/{slug}", response_class=HTMLResponse)
async def docs_page(request: Request, slug: str, lang: str = "de"):
    slug = _normalize_slug(slug)
    docs = _discover_docs()
    current_index = None
    current_doc = None

    for index, doc in enumerate(docs):
        if doc["slug"] == slug:
            current_index = index
            current_doc = doc
            break

    if current_doc is None:
        raise HTTPException(status_code=404, detail="Documentation page not found")

    # Determine which file to serve based on language
    doc_path = _get_doc_path(slug, lang, docs)
    if doc_path is None:
        doc_path = current_doc["path"]

    html, toc_html = _render_markdown(doc_path)
    previous_doc = docs[current_index - 1] if current_index > 0 else None
    next_doc = docs[current_index + 1] if current_index < len(docs) - 1 else None

    return templates.TemplateResponse(
        "docs-layout.html",
        {
            "request": request,
            "docs": docs,
            "current_doc": current_doc,
            "content_html": html,
            "toc_html": toc_html,
            "previous_doc": previous_doc,
            "next_doc": next_doc,
            "main_app_url": _docs_base_url(request),
            "current_lang": lang,
            "has_english": current_doc.get("has_english", False),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
