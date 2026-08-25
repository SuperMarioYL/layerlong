"""layerlong Web 预览（m3 stub）。

最小可用：粘贴 markdown → 分层 SVG 长图 → 浏览器侧 PNG 导出。
完整 live-edit + per-layer diff 高亮的交互在 m3 完整实现；此处提供
渲染 + 导出的可用骨架，让陌生人能在浏览器里 60 秒内看到第一张分层长图。

启动：``uvicorn layerlong.web:app`` 或 ``layerlong serve``（见 cli 占位）。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .parser import parse_markdown
from .renderer import render_html, render_svg

_BASE = Path(__file__).parent
_TEMPLATES = _BASE / "templates"
_STATIC = _BASE / "static"

app = FastAPI(title="layerlong preview", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """预览页：markdown 输入框 + 渲染结果 + PNG 导出。"""
    html = (_TEMPLATES / "preview.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.post("/render", response_class=JSONResponse)
async def render(req: Request) -> JSONResponse:
    """输入 markdown → 分层 SVG/HTML 长图（每图层可寻址）。"""
    form = await req.form()
    markdown = str(form.get("markdown", ""))
    platform = str(form.get("platform", "gzh"))
    if platform not in ("gzh", "xhs"):
        platform = "gzh"
    doc = parse_markdown(markdown, platform=platform)  # type: ignore[arg-type]
    return JSONResponse(
        {
            "svg": render_svg(doc),
            "html": render_html(doc),
            "title": doc.meta.title,
            "canvas": {"w": doc.meta.canvas.w, "h": doc.meta.canvas.h},
            "layer_count": len(doc.layers),
        }
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("layerlong.web:app", host="0.0.0.0", port=8000, reload=False)
