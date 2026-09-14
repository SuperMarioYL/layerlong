"""Web 预览 per-layer diff 的回归测试（v0.2.0 fix-web-preview-per-layer-diff）。

修复前：/render 只接受 markdown+platform，预览页无法展示 diff（m3 的
"改一数 → 看到 diff" 闭环只能在 CLI 完成）；且 starlette 表单解析需要的
python-multipart 未声明，全新安装下 POST /render 直接 AssertionError。
"""

import unittest

from click.testing import CliRunner

try:
    from fastapi.testclient import TestClient
except ImportError:  # 防御：HTTP 客户端缺席时跳过路由级测试
    TestClient = None

from layerlong.cli import cli
from layerlong.web import app, build_render_response

SAMPLE = """# 2024 增长复盘
## 关键指标
stat: 月活用户 | 1280 | 万
stat: 增长率 | 23.5 | %
stat: 留存率 | 68 | %
---
> 数据来源：内部统计
"""
SAMPLE_CHANGED = SAMPLE.replace("23.5", "31.2")


class TestBuildRenderResponse(unittest.TestCase):
    def test_no_prev_renders_clean(self):
        r = build_render_response(SAMPLE)
        self.assertEqual(r["changed_ids"], [])
        self.assertNotIn("svg_diff", r)
        self.assertNotIn("diff-highlight", r["svg"])
        self.assertEqual(r["layer_count"], 7)
        self.assertEqual(r["title"], "2024 增长复盘")

    def test_prev_highlights_exactly_changed_layers(self):
        r = build_render_response(SAMPLE_CHANGED, platform="gzh", prev_markdown=SAMPLE)
        self.assertEqual(r["changed_ids"], ["stat-1"])
        self.assertEqual(r["n_changed"], 1)
        # 干净 SVG 永远不带高亮（PNG 导出用）；高亮只在 svg_diff。
        self.assertEqual(r["svg"].count("diff-highlight"), 0)
        self.assertEqual(r["svg_diff"].count("diff-highlight"), 1)
        self.assertIn("1 /", r["html"])  # diff 横幅
        self.assertIn('id="stat-1"', r["svg_diff"])

    def test_identical_prev_reports_no_change(self):
        r = build_render_response(SAMPLE, prev_markdown=SAMPLE)
        self.assertEqual(r["changed_ids"], [])
        self.assertEqual(r["svg_diff"].count("diff-highlight"), 0)

    def test_unknown_platform_falls_back_to_gzh(self):
        r = build_render_response(SAMPLE, platform="bogus")
        self.assertEqual(r["canvas"]["w"], 750.0)  # gzh 预设宽


@unittest.skipUnless(TestClient is not None, "fastapi TestClient HTTP stack unavailable")
class TestRenderRoute(unittest.TestCase):
    """路由级验证（含 python-multipart 表单解析——修复前在此断言失败）。"""

    def test_route_full_diff_flow(self):
        client = TestClient(app)
        r1 = client.post("/render", data={"markdown": SAMPLE, "platform": "gzh"})
        self.assertEqual(r1.status_code, 200, r1.text)
        d1 = r1.json()
        self.assertEqual(d1["changed_ids"], [])
        self.assertNotIn("svg_diff", d1)

        r2 = client.post(
            "/render",
            data={"markdown": SAMPLE_CHANGED, "platform": "gzh", "prev_markdown": SAMPLE},
        )
        self.assertEqual(r2.status_code, 200, r2.text)
        d2 = r2.json()
        self.assertEqual(d2["changed_ids"], ["stat-1"])
        self.assertIn("diff-highlight", d2["svg_diff"])
        self.assertNotIn("diff-highlight", d2["svg"])

    def test_health(self):
        client = TestClient(app)
        self.assertEqual(client.get("/health").json(), {"status": "ok"})


class TestServeCommand(unittest.TestCase):
    def test_serve_is_listed_and_documented(self):
        runner = CliRunner()
        help_text = runner.invoke(cli, ["--help"]).output
        self.assertIn("serve", help_text)
        # 不真正起服务器，只验证选项解析。
        serve_help = runner.invoke(cli, ["serve", "--help"]).output
        self.assertIn("--host", serve_help)
        self.assertIn("--port", serve_help)


if __name__ == "__main__":
    unittest.main()
