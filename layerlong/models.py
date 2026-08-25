"""LayerDoc 数据模型 — 可编辑、可 diff 的分层长图文档。

每个视觉元素（标题块、数据行、标注、图表、分割线）是一个具名、可寻址的图层；
改一个数据点只影响映射到它的图层，diff 在图层粒度可见。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

LayerKind = Literal["title", "text", "stat", "chart", "annotation", "divider"]
RenderKind = Literal["svg", "html"]
Platform = Literal["gzh", "xhs"]
SourceKind = Literal["markdown", "csv", "text-extract"]


class BBox(BaseModel):
    """长图坐标空间内的一个矩形区域。"""

    x: float = 0
    y: float = 0
    w: float = 0
    h: float = 0


class Canvas(BaseModel):
    """画布尺寸（像素）。宽度由平台预设固定，高度随内容增长。"""

    w: float
    h: float


class Meta(BaseModel):
    """文档元信息：标题、目标平台、画布、标题安全区。"""

    title: str = "Untitled"
    platform: Platform = "gzh"
    canvas: Canvas
    safe_zones: list[BBox] = Field(default_factory=list)


class Layer(BaseModel):
    """一个具名、可寻址的图层。

    id 在文档内稳定唯一，diff 按 id 配对。改一个数据点只改变其映射图层的 data。
    """

    id: str
    kind: LayerKind = "text"
    bbox: BBox = Field(default_factory=BBox)
    data: dict = Field(default_factory=dict)
    render: RenderKind = "svg"


class DataSource(BaseModel):
    """数据来源记录：抽取是一次性的，产出作者拥有的已保存源。"""

    kind: SourceKind = "markdown"
    path: str = ""
    mapping: dict = Field(default_factory=dict)


class LayerDoc(BaseModel):
    """分层长图文档——layerlong 的核心原语。

    渲染器把 LayerDoc 投影成 (1) 合成 SVG（每图层一个 ``<g id>``）或
    (2) HTML 长图（每图层一个 ``<section id>``）。diff 作用于两个 LayerDoc，
    输出 per-layer 变化集，渲染器只重渲变化图层。
    """

    meta: Meta
    layers: list[Layer] = Field(default_factory=list)
    sources: list[DataSource] = Field(default_factory=list)


# 平台画布预设：公众号宽 750、小红书宽 1080（竖屏长宽比）。
# safe_zones 编码标题安全区——这是中文平台 surface 适配，非全球工具的汉化。
PLATFORM_PRESETS: dict[Platform, dict] = {
    "gzh": {
        "canvas_w": 750.0,
        "margin": 40.0,
        "title_safe": BBox(x=0, y=0, w=750, h=80),
    },
    "xhs": {
        "canvas_w": 1080.0,
        "margin": 56.0,
        "title_safe": BBox(x=0, y=0, w=1080, h=120),
    },
}


def canvas_for(platform: Platform) -> Canvas:
    """返回平台默认画布（高度占位，渲染时会按内容重算）。"""
    return Canvas(w=PLATFORM_PRESETS[platform]["canvas_w"], h=2000.0)


def wrap_text(text: str, max_chars: int) -> list[str]:
    """把文本按字符宽度折行，返回行列表。

    中文按字符计宽（无词边界），故按 max_chars 硬折；已有换行保留。
    renderer 与 parser 共用此函数，保证 bbox 高度与实际渲染行数一致。
    """
    if not text:
        return [""]
    lines: list[str] = []
    for raw in str(text).split("\n"):
        if len(raw) <= max_chars:
            lines.append(raw)
            continue
        buf = ""
        for ch in raw:
            buf += ch
            if len(buf) >= max_chars:
                lines.append(buf)
                buf = ""
        if buf:
            lines.append(buf)
    return lines or [""]
