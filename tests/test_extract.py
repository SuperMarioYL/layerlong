"""mock 抽取的回归测试（v0.4.0 m4）。

修复前：extract_mock 只要行内出现数字（且 ≤40 字）就当作 stat，而
_heuristic_stat 无法解析时返回占位 "{s} |  | "——于是一句普通叙述
（"我们在 2023 年完成了三次改版…"）被渲染成一个标签是整句、值为空的
stat 图层，并从正文流里消失。修复后无法析出数值的行回退为正文字段。
"""

import unittest
import xml.etree.ElementTree as ET

from layerlong.extract import extract_mock
from layerlong.renderer import render_svg

NARRATIVE = "我们在 2023 年完成了三次改版，转化率明显提升。"


def _layers_by_kind(doc):
    out = {}
    for layer in doc.layers:
        out.setdefault(layer.kind, []).append(layer)
    return out


class TestMockExtraction(unittest.TestCase):
    def test_narrative_sentence_stays_body_text(self):
        doc = extract_mock("2024 增长复盘\n" + NARRATIVE + "\n月活用户 1280万\n")
        stats = _layers_by_kind(doc).get("stat", [])
        # 修复前会多出一个 {"label": 整句, "value": "", "unit": ""} 的 stat。
        self.assertTrue(all(s.data["value"] for s in stats), [s.data for s in stats])
        bodies = [l.data.get("text", "") for l in _layers_by_kind(doc).get("text", [])]
        self.assertIn(NARRATIVE, bodies)

    def test_numeric_lines_still_become_stats(self):
        doc = extract_mock("2024 增长复盘\n月活用户 1280万\n营收 1280\n")
        stats = {s.data["label"]: (s.data["value"], s.data["unit"]) for s in _layers_by_kind(doc)["stat"]}
        self.assertEqual(stats["月活用户"], ("1280", "万"))
        self.assertEqual(stats["营收"], ("1280", ""))

    def test_output_still_renders(self):
        doc = extract_mock("2024 增长复盘\n" + NARRATIVE + "\n月活用户 1280万\n")
        ET.fromstring(render_svg(doc))


if __name__ == "__main__":
    unittest.main()
