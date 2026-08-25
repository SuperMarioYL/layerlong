"""markdown/CSV → LayerDoc 解析器。

支持的 markdown schema：
  ``# 标题``            → title 图层
  ``## 分段``           → section（text 图层，role=section）
  普通行               → body（text 图层）
  ``stat: 标签 | 值 | 单位``  → stat 图层
  ``---``              → divider 图层
  ``> 标注``            → annotation 图层

图层 id 按种类顺序稳定编号（stat-0/stat-1…），故改一个值不改变结构时
id 保持稳定——这是 diff 能精确配对的前提。
"""

from __future__ import annotations

import csv
import io

from .models import (
    BBox,
    Canvas,
    DataSource,
    Layer,
    LayerDoc,
    Meta,
    PLATFORM_PRESETS,
    Platform,
    wrap_text,
)

# 每类图层的高度与后续间距（像素）。
_HEIGHTS = {
    "title": 96.0,
    "section": 54.0,
    "body_line": 26.0,
    "stat": 58.0,
    "divider": 22.0,
    "annotation": 46.0,
    "chart": 160.0,
}
_GAPS = {
    "title": 18.0,
    "section": 16.0,
    "body": 14.0,
    "stat": 10.0,
    "divider": 14.0,
    "annotation": 14.0,
    "chart": 16.0,
}


def _max_chars(content_w: float) -> int:
    # 中文按 ~15px/字计；留余量，最低 10 字/行。
    return max(10, int(content_w / 15))


def _make_layer(
    lid: str, kind: str, data: dict, bbox: BBox, render: str = "svg"
) -> Layer:
    return Layer(id=lid, kind=kind, bbox=bbox, data=data, render=render)


def parse_markdown(text: str, platform: Platform = "gzh", title: str | None = None) -> LayerDoc:
    """把 markdown 文本解析为 LayerDoc，按平台画布做垂直排版。"""
    preset = PLATFORM_PRESETS[platform]
    cw = preset["canvas_w"]
    margin = preset["margin"]
    content_w = cw - 2 * margin
    max_chars = _max_chars(content_w)

    layers: list[Layer] = []
    counters: dict[str, int] = {}
    y = 40.0
    doc_title = title

    def next_id(kind_name: str) -> str:
        n = counters.get(kind_name, 0)
        counters[kind_name] = n + 1
        return f"{kind_name}-{n}"

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("# ") and not stripped.startswith("## "):
            t = stripped[2:].strip()
            if doc_title is None:
                doc_title = t
            h = _HEIGHTS["title"]
            layers.append(
                _make_layer("title", "title", {"text": t}, BBox(x=margin, y=y, w=content_w, h=h))
            )
            y += h + _GAPS["title"]
        elif stripped.startswith("## "):
            t = stripped[3:].strip()
            h = _HEIGHTS["section"]
            layers.append(
                _make_layer(
                    next_id("section"), "text",
                    {"text": t, "role": "section"}, BBox(x=margin, y=y, w=content_w, h=h),
                )
            )
            y += h + _GAPS["section"]
        elif stripped == "---":
            h = _HEIGHTS["divider"]
            layers.append(
                _make_layer(next_id("divider"), "divider", {}, BBox(x=margin, y=y, w=content_w, h=h))
            )
            y += h + _GAPS["divider"]
        elif stripped.startswith("> "):
            t = stripped[2:].strip()
            h = _HEIGHTS["annotation"]
            layers.append(
                _make_layer(
                    next_id("annotation"), "annotation", {"text": t},
                    BBox(x=margin, y=y, w=content_w, h=h),
                )
            )
            y += h + _GAPS["annotation"]
        elif stripped.lower().startswith("stat:"):
            data = _parse_stat(stripped[5:].strip())
            h = _HEIGHTS["stat"]
            layers.append(
                _make_layer(next_id("stat"), "stat", data, BBox(x=margin, y=y, w=content_w, h=h))
            )
            y += h + _GAPS["stat"]
        elif stripped.lower().startswith("chart:"):
            data = _parse_chart(stripped[6:].strip())
            h = _HEIGHTS["chart"] if data.get("values") else _HEIGHTS["body_line"]
            layers.append(
                _make_layer(next_id("chart"), "chart", data, BBox(x=margin, y=y, w=content_w, h=h))
            )
            y += h + _GAPS["chart"]
        else:
            lines = wrap_text(stripped, max_chars)
            h = _HEIGHTS["body_line"] * len(lines) + 8
            layers.append(
                _make_layer(
                    next_id("text"), "text", {"text": stripped, "lines": lines},
                    BBox(x=margin, y=y, w=content_w, h=h),
                )
            )
            y += h + _GAPS["body"]

    total_h = max(y + 40, 800.0)
    meta = Meta(
        title=doc_title or "Untitled",
        platform=platform,
        canvas=Canvas(w=cw, h=total_h),
        safe_zones=[preset["title_safe"]],
    )
    return LayerDoc(
        meta=meta,
        layers=layers,
        sources=[DataSource(kind="markdown", path="", mapping={})],
    )


def _parse_stat(rest: str) -> dict:
    """解析 ``标签 | 值 | 单位``（单位可省）。"""
    parts = [p.strip() for p in rest.split("|")]
    label = parts[0] if parts else ""
    value = parts[1] if len(parts) > 1 else ""
    unit = parts[2] if len(parts) > 2 else ""
    return {"label": label, "value": value, "unit": unit}


def _parse_chart(rest: str) -> dict:
    """解析 ``标签,值; 标签,值; ...`` 为柱状图数据。"""
    bars = []
    for item in rest.split(";"):
        item = item.strip()
        if not item:
            continue
        if "," in item:
            lab, val = item.split(",", 1)
            bars.append({"label": lab.strip(), "value": val.strip()})
        else:
            bars.append({"label": str(len(bars)), "value": item})
    return {"values": bars}


def parse_csv(text: str, platform: Platform = "gzh", title: str | None = None) -> LayerDoc:
    """把 CSV 解析为 LayerDoc：首行为表头，后续每行一个 stat 图层。"""
    preset = PLATFORM_PRESETS[platform]
    cw = preset["canvas_w"]
    margin = preset["margin"]
    content_w = cw - 2 * margin

    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if any(c.strip() for c in r)]
    if not rows:
        return parse_markdown("# 空文档\n", platform=platform, title=title)

    header = [c.strip() for c in rows[0]]
    # 期望列: label, value, unit（按表头名匹配，缺失则按位置）。
    def col(name: str, fallback: int) -> int:
        if name in header:
            return header.index(name)
        return fallback if fallback < len(header) else fallback

    li, vi, ui = col("label", 0), col("value", 1), col("unit", 2)
    doc_title = title or header[0]

    layers: list[Layer] = []
    y = 40.0
    for i, row in enumerate(rows[1:]):
        label = row[li].strip() if li < len(row) else ""
        value = row[vi].strip() if vi < len(row) else ""
        unit = row[ui].strip() if ui < len(row) else ""
        # 标题行（首列空、值非空）当 section。
        if not label and value:
            layers.append(
                _make_layer(
                    f"section-{i}", "text", {"text": value, "role": "section"},
                    BBox(x=margin, y=y, w=content_w, h=_HEIGHTS["section"]),
                )
            )
            y += _HEIGHTS["section"] + _GAPS["section"]
            continue
        layers.append(
            _make_layer(
                f"stat-{i}", "stat", {"label": label, "value": value, "unit": unit},
                BBox(x=margin, y=y, w=content_w, h=_HEIGHTS["stat"]),
            )
        )
        y += _HEIGHTS["stat"] + _GAPS["stat"]

    total_h = max(y + 40, 800.0)
    meta = Meta(
        title=doc_title or "Untitled",
        platform=platform,
        canvas=Canvas(w=cw, h=total_h),
        safe_zones=[preset["title_safe"]],
    )
    return LayerDoc(
        meta=meta,
        layers=layers,
        sources=[DataSource(kind="csv", path="", mapping={})],
    )
