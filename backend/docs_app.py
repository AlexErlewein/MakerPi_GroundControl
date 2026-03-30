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
    docs = []
    for file_path in files:
        slug = _clean_slug(file_path.stem)
        docs.append({
            "slug": slug,
            "title": _extract_title(file_path),
            "path": file_path,
        })
    return docs


def _normalize_slug(slug: str) -> str:
    normalized = slug.strip().strip("/")
    if normalized.endswith(".md"):
        normalized = normalized[:-3]
    normalized = Path(normalized).stem
    return _clean_slug(normalized)


def _render_markdown(path: Path):
    md = markdown.Markdown(
        extensions=["toc", "tables", "fenced_code", "attr_list", "sane_lists"],
        extension_configs={"toc": {"permalink": True}},
    )
    source = path.read_text(encoding="utf-8")
    html = md.convert(source)
    return html, md.toc


def _docs_base_url(request: Request) -> str:
    hostname = request.url.hostname or "localhost"
    return f"{request.url.scheme}://{hostname}:8000"


@app.get("/health")
async def health():
    return {"ok": True, "docs_count": len(_discover_docs())}


@app.get("/", response_class=HTMLResponse)
async def docs_index():
    docs = _discover_docs()
    if not docs:
        raise HTTPException(status_code=404, detail="No documentation pages found")
    return RedirectResponse(url=f"/page/{docs[0]['slug']}", status_code=307)


@app.get("/page/{slug}", response_class=HTMLResponse)
async def docs_page(request: Request, slug: str):
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

    html, toc_html = _render_markdown(current_doc["path"])
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
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
