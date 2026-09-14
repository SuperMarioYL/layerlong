"""CLI 输入加载的回归测试（v0.2.0 fix-cli-input-loading）。

修复前：坏 JSON 输入（render --prev / diff / *.json 输入）直接抛出 pydantic
原始 traceback；无显式标题的 CSV 把首列列头名（"label"）当文档标题。
全部用 click.testing.CliRunner 进程内运行，不起子进程。
"""

import json
import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner

from layerlong.cli import cli
from layerlong.parser import parse_csv

REPO = Path(__file__).resolve().parent.parent
SAMPLE = REPO / "examples" / "sample.md"
CSV_TEXT = "label,value,unit\n月活用户,1280,万\n增长率,23.5,%\n"


class TestCliBadInput(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _bad_json(self) -> Path:
        p = self.tmpdir / "bad.json"
        p.write_text("not json", encoding="utf-8")
        return p

    def test_render_prev_bad_json_is_friendly_error(self):
        out = self.tmpdir / "out1"
        r = self.runner.invoke(
            cli, ["render", str(SAMPLE), "--prev", str(self._bad_json()), "-o", str(out)]
        )
        self.assertEqual(r.exit_code, 1)
        self.assertIn("无法加载", r.output)
        self.assertNotIn("Traceback", r.output)
        self.assertNotIn("ValidationError", r.output)

    def test_render_bad_input_json_is_friendly_error(self):
        r = self.runner.invoke(cli, ["render", str(self._bad_json()), "-o", str(self.tmpdir / "out2")])
        self.assertEqual(r.exit_code, 1)
        self.assertIn("无法加载", r.output)
        self.assertNotIn("Traceback", r.output)

    def test_diff_bad_json_is_friendly_error(self):
        good = self.tmpdir / "good.json"
        r0 = self.runner.invoke(cli, ["render", str(SAMPLE), "-o", str(self.tmpdir / "out3")])
        self.assertEqual(r0.exit_code, 0)
        good.write_text((self.tmpdir / "out3" / "long.json").read_text(encoding="utf-8"), encoding="utf-8")
        r = self.runner.invoke(cli, ["diff", str(self._bad_json()), str(good)])
        self.assertEqual(r.exit_code, 1)
        self.assertIn("无法加载", r.output)
        self.assertNotIn("Traceback", r.output)


class TestCliHappyPath(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_render_writes_outputs_and_diff_self_is_zero(self):
        out = self.tmpdir / "out"
        r = self.runner.invoke(cli, ["render", str(SAMPLE), "-o", str(out)])
        self.assertEqual(r.exit_code, 0, r.output)
        for name in ("long.json", "long.svg", "long.html"):
            self.assertTrue((out / name).exists(), name)

        r2 = self.runner.invoke(cli, ["diff", str(out / "long.json"), str(out / "long.json")])
        self.assertEqual(r2.exit_code, 0, r2.output)
        self.assertIn("0 /", r2.output)

    def test_render_csv_titles_document_with_filename(self):
        csv_path = self.tmpdir / "数据表.csv"
        csv_path.write_text(CSV_TEXT, encoding="utf-8")
        out = self.tmpdir / "out"
        r = self.runner.invoke(cli, ["render", str(csv_path), "-o", str(out)])
        self.assertEqual(r.exit_code, 0, r.output)
        meta = json.loads((out / "long.json").read_text(encoding="utf-8"))["meta"]
        self.assertEqual(meta["title"], "数据表")  # 修复前是首列列头 "label"

    def test_parse_csv_without_title_is_untitled(self):
        doc = parse_csv(CSV_TEXT)
        self.assertEqual(doc.meta.title, "Untitled")  # 修复前是 "label"


if __name__ == "__main__":
    unittest.main()
