"""per-layer diff 与渲染的验证测试。

验证 m2 硬指标：改一个 stat，diff 只标 1 层、渲染器只高亮那一层；
产物是机器可验的可编辑分层 SVG/HTML，非扁平 PNG。
"""

import unittest
import xml.etree.ElementTree as ET

from layerlong.diff import changed_set, diff_docs
from layerlong.models import LayerDoc
from layerlong.parser import parse_csv, parse_markdown
from layerlong.renderer import render_diff_html, render_html, render_svg

SAMPLE = """# 2024 增长复盘
## 关键指标
stat: 月活用户 | 1280 | 万
stat: 增长率 | 23.5 | %
stat: 留存率 | 68 | %
---
> 数据来源：内部统计
"""


class TestDiff(unittest.TestCase):
    def test_change_one_stat_diffs_exactly_one_layer(self):
        a = parse_markdown(SAMPLE, platform="gzh")
        b = parse_markdown(SAMPLE.replace("23.5", "31.2"), platform="gzh")
        report = diff_docs(a, b)
        ids = report.changed_ids
        self.assertEqual(ids, ["stat-1"], f"expected only stat-1 changed, got {ids}")

    def test_unchanged_doc_has_no_diff(self):
        a = parse_markdown(SAMPLE)
        b = parse_markdown(SAMPLE)
        self.assertEqual(diff_docs(a, b).changed_ids, [])
        self.assertEqual(diff_docs(a, b).n_changed, 0)

    def test_adding_a_layer_is_detected_as_added(self):
        a = parse_markdown(SAMPLE)
        b = parse_markdown(SAMPLE + "stat: 转化率 | 4.1 | %\n")
        report = diff_docs(a, b)
        added = [c.id for c in report.added]
        self.assertIn("stat-3", added)
        self.assertEqual(report.n_changed, 1)

    def test_removing_a_layer_is_detected_as_removed(self):
        a = parse_markdown(SAMPLE + "stat: 转化率 | 4.1 | %\n")
        b = parse_markdown(SAMPLE)
        report = diff_docs(a, b)
        removed = [c.id for c in report.removed]
        self.assertIn("stat-3", removed)

    def test_bbox_layout_change_is_not_a_semantic_diff(self):
        # 排版重排（坐标变化）不算语义变化。
        a = parse_markdown(SAMPLE, platform="gzh")
        b = parse_markdown(SAMPLE, platform="xhs")
        # 平台不同→坐标/尺寸不同，但 data 相同→无语义 diff。
        report = diff_docs(a, b)
        self.assertEqual(report.changed_ids, [])


class TestRenderer(unittest.TestCase):
    def test_svg_well_formed(self):
        doc = parse_markdown(SAMPLE)
        svg = render_svg(doc)
        # 可被 XML 解析器解析 = 语法正确的分层 SVG。
        ET.fromstring(svg)

    def test_each_layer_is_addressable_group(self):
        doc = parse_markdown(SAMPLE)
        svg = render_svg(doc)
        root = ET.fromstring(svg)
        ns = "{http://www.w3.org/2000/svg}"
        g_ids = [g.get("id") for g in root.iter(ns + "g")]
        self.assertIn("title", g_ids)
        self.assertIn("stat-0", g_ids)
        self.assertIn("stat-1", g_ids)
        self.assertIn("stat-2", g_ids)

    def test_diff_render_highlights_exactly_one_layer(self):
        a = parse_markdown(SAMPLE)
        b = parse_markdown(SAMPLE.replace("23.5", "31.2"))
        report = diff_docs(a, b)
        hl = changed_set(report)
        self.assertEqual(hl, {"stat-1"})
        svg = render_svg(b, highlight=hl)
        # 恰好一个 diff-highlight 高亮框（只有 stat-1）。
        self.assertEqual(svg.count("diff-highlight"), 1)
        # 高亮的图层确实存在。
        self.assertIn('id="stat-1"', svg)
        # 未变化的图层不被高亮。
        self.assertNotIn("diff-highlight", render_svg(b, highlight=set()))

    def test_diff_html_highlights_changed_only(self):
        a = parse_markdown(SAMPLE)
        b = parse_markdown(SAMPLE.replace("23.5", "31.2"))
        report = diff_docs(a, b)
        html = render_diff_html(b, report)
        self.assertIn('id="stat-1"', html)
        self.assertIn("layer-changed", html)
        # 变化横幅出现且只报告 1 层。
        self.assertIn("1 /", html)

    def test_html_well_formed_sections(self):
        doc = parse_markdown(SAMPLE)
        html = render_html(doc)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn('id="stat-1"', html)
        self.assertIn("layer-stat", html)


class TestCsvAndRoundtrip(unittest.TestCase):
    def test_csv_parses_to_stat_layers(self):
        csv_text = "label,value,unit\n月活用户,1280,万\n增长率,23.5,%\n"
        doc = parse_csv(csv_text, platform="gzh")
        ids = [l.id for l in doc.layers]
        self.assertEqual(ids, ["stat-0", "stat-1"])

    def test_layerdoc_json_roundtrip(self):
        doc = parse_markdown(SAMPLE)
        js = doc.model_dump_json()
        back = LayerDoc.model_validate_json(js)
        self.assertEqual(diff_docs(doc, back).n_changed, 0)

    def test_render_after_roundtrip(self):
        doc = parse_markdown(SAMPLE)
        back = LayerDoc.model_validate_json(doc.model_dump_json())
        ET.fromstring(render_svg(back))


if __name__ == "__main__":
    unittest.main()
