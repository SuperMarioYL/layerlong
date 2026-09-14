"""LayerDoc → 分层 SVG/HTML 长图渲染器。

SVG 产物每图层是一个可寻址的 ``<g id="...">``；HTML 产物每图层是一个
``<section id="...">``。diff 模式只高亮变化图层——这是"改一处数据，
只重渲一层"的物化。
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .diff import DiffReport, changed_set
from .models import LayerDoc, wrap_text

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def chart_bar_pcts(bars: list) -> list[float]:
    """把图表条目换算为相对本图最大值的百分比条宽（SVG/HTML 两种导出共用）。

    每条 = max(2, 100 * value / max_value)，上限 100；非数值或非正的
    最大值整体退化为 2% 最小条宽——条长必须反映数据本身。
    """
    values: list[float] = []
    for b in bars:
        try:
            values.append(float(b.get("value", "")))
        except (TypeError, ValueError):
            values.append(0.0)
    max_v = max(values, default=0.0)
    if max_v <= 0:
        return [2.0] * len(bars)
    return [max(2.0, min(100.0, 100.0 * v / max_v)) for v in values]


_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml", "svg", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)
_env.filters["wrap"] = wrap_text
_env.filters["chart_pcts"] = chart_bar_pcts

# 长图调色（独立于 README house style，是导出产物自身的视觉）。
PALETTE = {
    "bg": "#FBFBFD",
    "title": "#1D1D1F",
    "section": "#0071E3",
    "text": "#1D1D1F",
    "muted": "#6E6E73",
    "value": "#0071E3",
    "divider": "#E5E5EA",
    "annotation_bar": "#6E6E73",
    "highlight": "#FF9500",
    "chart": "#0071E3",
}


def render_svg(doc: LayerDoc, highlight: set[str] | None = None) -> str:
    """LayerDoc → 分层 SVG（每图层 ``<g id>``）。

    highlight 中的图层会被加上 diff 高亮框——渲染器据此只重渲/高亮变化图层。
    """
    tpl = _env.get_template("long.svg.j2")
    return tpl.render(doc=doc, highlight=highlight or set(), colors=PALETTE)


def render_html(
    doc: LayerDoc,
    highlight: set[str] | None = None,
    diff_info: tuple[int, int] | None = None,
) -> str:
    """LayerDoc → 分层 HTML 长图（每图层 ``<section id>``）。

    diff_info=(n_changed, n_total) 时在顶部渲染一个 diff 横幅。
    """
    highlight = highlight or set()
    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        "<head>",
        '<meta charset="utf-8">',
        f"<title>{_esc(doc.meta.title)}</title>",
        "<style>",
        _HTML_CSS,
        "</style>",
        "</head>",
        "<body>",
        f'<div class="layerlong-long" style="width:{int(doc.meta.canvas.w)}px">',
    ]
    if diff_info is not None:
        n_changed, n_total = diff_info
        parts.append(
            f'<div class="diff-banner">{n_changed} / {n_total} 图层变化'
            f'{" · 只重渲变化层" if n_changed else " · 无变化"}</div>'
        )
    for layer in doc.layers:
        cls = "layer"
        if layer.id in highlight:
            cls += " layer-changed"
        parts.append(
            f'<section id="{_esc(layer.id)}" class="{cls} layer-{layer.kind}">'
        )
        parts.append(_render_layer_html(layer))
        parts.append("</section>")
    parts.append("</div>")
    parts.append("</body></html>")
    return "\n".join(parts)


def render_diff_html(doc: LayerDoc, report: DiffReport) -> str:
    """渲染当前版本，仅高亮变化图层 + diff 横幅。"""
    hl = changed_set(report)
    return render_html(doc, highlight=hl, diff_info=(report.n_changed, len(doc.layers)))


def _render_layer_html(layer) -> str:
    k = layer.kind
    d = layer.data
    if k == "title":
        return f'<h1 class="ll-title">{_esc(d.get("text", ""))}</h1>'
    if k == "text":
        if d.get("role") == "section":
            return f'<h2 class="ll-section">{_esc(d.get("text", ""))}</h2>'
        text = d.get("text", "")
        return f'<p class="ll-body">{_esc(text)}</p>'
    if k == "stat":
        return (
            '<div class="ll-stat">'
            f'<span class="ll-stat-label">{_esc(d.get("label", ""))}</span>'
            f'<span class="ll-stat-value">{_esc(d.get("value", ""))}'
            f' <small>{_esc(d.get("unit", ""))}</small></span>'
            "</div>"
        )
    if k == "divider":
        return '<hr class="ll-divider">'
    if k == "annotation":
        return f'<aside class="ll-annotation">{_esc(d.get("text", ""))}</aside>'
    if k == "chart":
        bars = d.get("values", [])
        if not bars:
            return ""
        pcts = chart_bar_pcts(bars)
        rows = "".join(
            f'<div class="ll-bar-row"><span class="ll-bar-label">{_esc(b.get("label",""))}</span>'
            f'<div class="ll-bar-track"><div class="ll-bar-fill" style="width:{pcts[i]:.1f}%"></div></div>'
            f'<span class="ll-bar-val">{_esc(b.get("value",""))}</span></div>'
            for i, b in enumerate(bars)
        )
        return f'<div class="ll-chart">{rows}</div>'
    return ""


def _esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


_HTML_CSS = """
*{box-sizing:border-box;margin:0}
body{background:#fff;font-family:"PingFang SC","Microsoft YaHei",-apple-system,sans-serif}
.layerlong-long{margin:0 auto;background:#FBFBFD;padding:40px;color:#1D1D1F}
.diff-banner{background:#FFF4E0;color:#9A6A00;border:1px solid #FFD9A0;border-radius:8px;padding:10px 14px;font-size:14px;font-weight:600;margin-bottom:16px}
.layer{padding:8px 0;border-radius:4px;transition:background .2s}
.layer-changed{background:#FFF7E8;box-shadow:inset 3px 0 0 #FF9500;padding-left:12px}
.ll-title{font-size:30px;font-weight:700;line-height:1.3;margin:6px 0}
.ll-section{font-size:20px;font-weight:600;color:#0071E3;margin:14px 0 6px;padding-bottom:6px;border-bottom:2px solid #E5E5EA}
.ll-body{font-size:15px;line-height:1.7;color:#1D1D1F;margin:4px 0}
.ll-stat{display:flex;justify-content:space-between;align-items:baseline;padding:10px 0;border-bottom:1px solid #F0F0F2}
.ll-stat-label{font-size:14px;color:#6E6E73}
.ll-stat-value{font-size:22px;font-weight:700;color:#0071E3}
.ll-stat-value small{font-size:13px;font-weight:500;color:#6E6E73}
.ll-divider{border:0;border-top:1px solid #E5E5EA;margin:14px 0}
.ll-annotation{border-left:3px solid #6E6E73;padding:4px 0 4px 12px;font-size:13px;color:#6E6E73;font-style:italic;margin:6px 0}
.ll-chart{margin:8px 0}
.ll-bar-row{display:flex;align-items:center;gap:10px;margin:6px 0}
.ll-bar-label{font-size:13px;color:#6E6E73;width:90px;flex-shrink:0}
.ll-bar-track{flex:1;height:14px;background:#F0F0F2;border-radius:7px;overflow:hidden}
.ll-bar-fill{height:100%;background:#0071E3;border-radius:7px}
.ll-bar-val{font-size:13px;font-weight:600;color:#1D1D1F;width:50px;text-align:right}
"""
