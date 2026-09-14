"""图表图层几何的回归测试（v0.2.0 fix-chart-geometry）。

修复前：SVG 导出把所有柱条画成固定 60% 宽（long.svg.j2 硬编码 0.6，与数值
无关）；图表层高固定 160px，超过 5 条时柱条压到下一图层。修复后条宽相对
本图最大值成比例，层高随条目数增长。
"""

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from layerlong.parser import parse_markdown
from layerlong.renderer import chart_bar_pcts, render_html, render_svg

REPO = Path(__file__).resolve().parent.parent
CHART_FILL = "#0071E3"
NS = "{http://www.w3.org/2000/svg}"


def _svg_bar_widths(markdown: str) -> list[float]:
    """渲染 markdown 并取出 chart-0 图层内着色柱条的宽度（像素）。"""
    doc = parse_markdown(markdown)
    svg = render_svg(doc)
    root = ET.fromstring(svg)  # 同时验证 SVG 仍可被 XML 解析
    chart_g = next(g for g in root.iter(NS + "g") if g.get("id") == "chart-0")
    track_w = float(chart_g.find(NS + "rect[@fill='#F0F0F2']").get("width"))
    widths = [
        float(r.get("width"))
        for r in chart_g.iter(NS + "rect")
        if r.get("fill") == CHART_FILL
    ]
    return [w / track_w * 100 for w in widths]  # 归一化为百分比，与 HTML 可比


class TestChartBarWidths(unittest.TestCase):
    def test_svg_bar_widths_proportional_to_values(self):
        pcts = _svg_bar_widths("# t\nchart: 甲,62; 乙,28; 丙,10\n")
        self.assertEqual(len(pcts), 3)
        self.assertEqual(pcts[0], 100.0)  # 最大值条占满
        self.assertGreater(pcts[1], pcts[2])
        # 修复前三条全部相同（固定 0.6 宽）；现在 10/62 ≈ 16.1%。
        self.assertAlmostEqual(pcts[2], 100.0 * 10 / 62, places=1)

    def test_shipped_sample_chart_renders_distinct_bars(self):
        md = (REPO / "examples" / "sample.md").read_text(encoding="utf-8")
        pcts = _svg_bar_widths(md)
        self.assertEqual(len(pcts), 3)  # 自然流量,62; 付费投放,28; 社交裂变,10
        self.assertEqual(len(set(pcts)), 3, f"bars must be distinct, got {pcts}")

    def test_large_values_do_not_saturate(self):
        pcts = _svg_bar_widths("# t\nchart: a,1280; b,900\n")
        self.assertEqual(pcts[0], 100.0)
        self.assertAlmostEqual(pcts[1], 100.0 * 900 / 1280, places=1)

    def test_html_and_svg_bar_widths_agree(self):
        md = "# t\nchart: a,62; b,10\n"
        doc = parse_markdown(md)
        html = render_html(doc)
        html_pcts = sorted(
            float(w) for w in re.findall(r"width:([\d.]+)%", html)
        )
        svg_pcts = sorted(_svg_bar_widths(md))
        self.assertEqual(len(html_pcts), len(svg_pcts))
        for a, b in zip(html_pcts, svg_pcts):
            self.assertAlmostEqual(a, b, places=1)

    def test_non_numeric_values_degrade_to_minimum(self):
        md = "# t\nchart: a,xx; b,yy\n"
        pcts = _svg_bar_widths(md)  # 不抛异常
        self.assertEqual(pcts, [2.0, 2.0])
        self.assertEqual(chart_bar_pcts([{"value": "x"}, {"value": "y"}]), [2.0, 2.0])

    def test_chart_helper_bounds(self):
        bars = [{"value": "50"}, {"value": "100"}]
        self.assertEqual(chart_bar_pcts(bars), [50.0, 100.0])
        self.assertEqual(chart_bar_pcts([]), [])


class TestChartLayerHeight(unittest.TestCase):
    def test_chart_height_scales_with_bar_count(self):
        md = "# t\nchart: a,1; b,2; c,3; d,4; e,5; f,6; g,7\n正文段落"
        doc = parse_markdown(md)
        _, chart, body = doc.layers
        self.assertEqual(chart.bbox.h, 20.0 + 30.0 * 7)  # 修复前固定 160
        # 最后一条柱条底边（y+10+6*30+16）必须落在图层 bbox 内，
        # 且下一图层起点在图表层底边之下——修复前会重叠 30px。
        last_bar_bottom = chart.bbox.y + 10 + 6 * 30 + 16
        self.assertLessEqual(last_bar_bottom, chart.bbox.y + chart.bbox.h)
        self.assertGreaterEqual(body.bbox.y, chart.bbox.y + chart.bbox.h)

    def test_empty_chart_keeps_body_line_height(self):
        doc = parse_markdown("# t\nchart: \n正文")
        chart = doc.layers[1]
        self.assertEqual(chart.bbox.h, 26.0)


if __name__ == "__main__":
    unittest.main()
