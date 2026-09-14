"""layerlong Web 预览（m3）。

完整 m3 闭环：粘贴 markdown → 分层长图 → 改一数据 → diff 高亮 → 浏览器侧
PNG 导出。/render 接受可选的 prev_markdown（上一次渲染的原文），提供
prev 时响应携带 per-layer 变化集与高亮版 SVG；PNG 导出始终用干净 SVG。

启动：``uvicorn layerlong.web:app`` 或 ``layerlong serve``。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .diff import changed_set, diff_docs
from .parser import parse_markdown
from .renderer import render_html, render_svg

_BASE = Path(__file__).parent
_TEMPLATES = _BASE / "templates"
_STATIC = _BASE / "static"

app = FastAPI(title="layerlong preview", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


def build_render_response(
    markdown: str, platform: str = "gzh", prev_markdown: str | None = None
) -> dict:
    """构造 /render 响应体（纯函数，脱离 HTTP 也可验证）。

    - svg 永远是干净版（无 diff 高亮）——浏览器侧 PNG 导出用。
    - 提供 prev_markdown 时：diff_docs 对比两版，响应附 changed_ids、
      n_changed、高亮版 svg_diff，html 换成带 diff 横幅的版本。
    """
    if platform not in ("gzh", "xhs"):
        platform = "gzh"
    doc = parse_markdown(markdown, platform=platform)  # type: ignore[arg-type]
    resp: dict = {
        "svg": render_svg(doc),
        "html": render_html(doc),
        "title": doc.meta.title,
        "canvas": {"w": doc.meta.canvas.w, "h": doc.meta.canvas.h},
        "layer_count": len(doc.layers),
        "changed_ids": [],
    }
    if prev_markdown:
        prev_doc = parse_markdown(prev_markdown, platform=platform)  # type: ignore[arg-type]
        report = diff_docs(prev_doc, doc)
        highlight = changed_set(report)
        resp["changed_ids"] = report.changed_ids
        resp["n_changed"] = report.n_changed
        resp["svg_diff"] = render_svg(doc, highlight=highlight)
        resp["html"] = render_html(doc, highlight=highlight, diff_info=(report.n_changed, len(doc.layers)))
    return resp


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """预览页：markdown 输入框 + 渲染结果 + per-layer diff + PNG 导出。"""
    html = (_TEMPLATES / "preview.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.post("/render", response_class=JSONResponse)
async def render(req: Request) -> JSONResponse:
    """输入 markdown（可选 prev_markdown）→ 分层长图 + per-layer diff。"""
    form = await req.form()
    prev = form.get("prev_markdown")
    return JSONResponse(
        build_render_response(
            markdown=str(form.get("markdown", "")),
            platform=str(form.get("platform", "gzh")),
            prev_markdown=str(prev) if prev else None,
        )
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("layerlong.web:app", host="0.0.0.0", port=8000, reload=False)
