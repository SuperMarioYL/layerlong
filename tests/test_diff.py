"""per-layer diff 与渲染的验证测试。

验证 m2 硬指标：改一个 stat，diff 只标 1 层、渲染器只高亮那一层；
产物是机器可验的可编辑分层 SVG/HTML，非扁平 PNG。
"""

import json
import unittest
import xml.etree.ElementTree as ET

from pydantic import ValidationError

from layerlong.diff import changed_set, diff_docs
from layerlong.models import BBox, Canvas, Layer, LayerDoc, Meta, wrap_text
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


NS = "{http://www.w3.org/2000/svg}"
# 208 字：gzh 内容宽 670 → 44 字/行 = 5 行；模板旧回退值 40 字/行 = 6 行。
PARAGRAPH = (
    "这是一段很长的正文内容用来检验渲染时的换行宽度是否与解析时一致"
    "所以需要足够多的字符来跨越不同折行阈值边界"
) * 4


class TestLayerIdUniqueness(unittest.TestCase):
    """v0.4.0 m1 回归：每个 title 图层曾共用硬编码 id "title"。

    修复前：`# ` 分支用字面量 id "title"（parser.py:94），两个 H1 的文档会产出
    两个 id 相同的图层——SVG/HTML 出现重复 id，diff_docs 的 id→layer 映射把
    后一个覆盖前一个，只改第二个标题却把两个标题都报成 changed 并同时高亮；
    且加载带重复 id 的 saved JSON 时静默接受。
    """

    DUP_MD = "# 主标题\n正文一\n# 副标题\n正文二\n"

    def test_two_h1_headings_get_distinct_layer_ids(self):
        doc = parse_markdown(self.DUP_MD)
        ids = [layer.id for layer in doc.layers]
        self.assertEqual(len(ids), 4, ids)
        self.assertEqual(len(set(ids)), 4, f"重复 id：{ids}")
        self.assertIn("title", ids)
        self.assertIn("title-1", ids)  # 与 stat-0/stat-1 同一编号约定

        root = ET.fromstring(render_svg(doc))
        g_ids = [g.get("id") for g in root.iter(NS + "g")]
        self.assertEqual(len(g_ids), len(set(g_ids)), f"SVG <g id> 重复：{g_ids}")
        self.assertEqual(render_html(doc).count('id="title"'), 1)

    def test_changing_second_h1_reports_one_layer(self):
        a = parse_markdown(self.DUP_MD)
        b = parse_markdown(self.DUP_MD.replace("副标题", "副标题改了"))
        report = diff_docs(a, b)
        # 修复前：changed_ids == ["title", "title"]，未改动的第一个标题也被高亮。
        self.assertEqual(report.changed_ids, ["title-1"])
        self.assertEqual(report.n_changed, 1)
        self.assertEqual(render_svg(b, highlight=changed_set(report)).count("diff-highlight"), 1)

    def test_duplicate_ids_rejected_on_load(self):
        doc = parse_markdown(self.DUP_MD)
        payload = json.loads(doc.model_dump_json())
        payload["layers"][2]["id"] = "title"  # 第二个标题复用第一个的 id
        with self.assertRaises(ValidationError):
            LayerDoc.model_validate_json(json.dumps(payload))


class TestDiffSummaryTotals(unittest.TestCase):
    """v0.4.0 m2 回归：摘要分母只数当前文档图层，删除图层时报出 >100%。

    修复前：n_changed 含 removed，分母却是 len(curr.layers)——删掉 4 层中的 3 层
    渲染成 "3 / 1 图层变化"，空文档甚至 "5 / 0"。
    """

    def test_removed_layers_count_in_the_total(self):
        prev = parse_markdown("# T\nstat: a | 1 | x\nstat: b | 2 | y\nstat: c | 3 | z\n")
        curr = parse_markdown("# T\n")
        report = diff_docs(prev, curr)
        self.assertEqual(report.n_changed, 3)
        self.assertEqual(report.n_total, 4)
        self.assertIn("3 / 4", render_diff_html(curr, report))

    def test_mixed_add_and_remove_total(self):
        prev = parse_markdown("# T\nstat: a | 1 | x\n")
        curr = parse_markdown("# T\n正文\n")
        report = diff_docs(prev, curr)
        self.assertEqual(report.n_changed, 2)  # stat-0 removed + text-0 added
        self.assertEqual(report.n_total, 3)  # + unchanged title
        self.assertIn("2 / 3", render_diff_html(curr, report))

    def test_no_removal_total_is_current_layer_count(self):
        a = parse_markdown(SAMPLE)
        b = parse_markdown(SAMPLE.replace("23.5", "31.2"))
        report = diff_docs(a, b)
        self.assertEqual(report.n_total, len(b.layers))
        self.assertIn("1 / 7", render_diff_html(b, report))


class TestTextWrapping(unittest.TestCase):
    """v0.4.0 m3 回归：折行结果曾被持久化进 Layer.data（"lines"）。

    修复前：(1) 改 saved JSON 的 text 后 SVG 仍渲染旧 lines，HTML 却显示新文本；
    (2) `lines` 依赖画布宽度，同一内容切 gzh/xhs 被 diff 判为语义变化，违背
    "仅坐标变化不计为语义变化"；(3) 无 lines 时模板按硬编码 40 字折行，与
    parser 的 max(10, 宽/15)=44 不一致，多出一行压到下一图层。
    """

    def test_platform_switch_is_not_a_semantic_change(self):
        md = "# 标题\n" + PARAGRAPH + "\n"
        a = parse_markdown(md, platform="gzh")
        b = parse_markdown(md, platform="xhs")
        self.assertEqual(diff_docs(a, b).changed_ids, [])
        # data 只放语义内容：折行是渲染期投影，不属于文档数据。
        self.assertNotIn("lines", a.layers[1].data)

    def test_edited_text_renders_in_svg_and_html(self):
        doc = parse_markdown("# 标题\n" + PARAGRAPH + "\n")
        stale_first_line = PARAGRAPH[:40]
        doc.layers[1].data["text"] = "全新的短句"
        svg = render_svg(doc)
        self.assertIn("全新的短句", svg)
        self.assertNotIn(stale_first_line, svg)
        self.assertIn("全新的短句", render_html(doc))

    def test_layer_without_lines_wraps_to_bbox_width(self):
        layer = Layer(
            id="text-0",
            kind="text",
            bbox=BBox(x=40, y=100, w=670, h=138),
            data={"text": PARAGRAPH},
        )
        doc = LayerDoc(meta=Meta(title="t", canvas=Canvas(w=750, h=400)), layers=[layer])
        root = ET.fromstring(render_svg(doc))
        g = next(x for x in root.iter(NS + "g") if x.get("id") == "text-0")
        # gzh 内容宽 670：44 字/行（5 行）。修复前按 40 字折行渲染出 6 行。
        tspans = list(g.iter(NS + "tspan"))
        self.assertEqual(len(tspans), len(wrap_text(PARAGRAPH, 44)))
        self.assertEqual(len(tspans), 5)


if __name__ == "__main__":
    unittest.main()
