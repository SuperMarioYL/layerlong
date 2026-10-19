"""版本一致性测试（v0.2.0 quality-version-lockstep-and-changelog）。

所有携带版本号的表面必须在 lockstep：VERSION 文件、pyproject [project]
version、__version__、web/site.json content_version、CHANGELOG 当前版本
节、FastAPI app 版本。未来 bump 漏改任何一处即失败。全部进程内断言，
无子进程。
"""

import json
import tomllib
import unittest
from pathlib import Path

import layerlong

REPO = Path(__file__).resolve().parent.parent
EXPECTED = "0.3.0"


class TestVersionLockstep(unittest.TestCase):
    def test_version_file(self):
        self.assertEqual((REPO / "VERSION").read_text(encoding="utf-8").strip(), EXPECTED)

    def test_pyproject_version(self):
        with open(REPO / "pyproject.toml", "rb") as f:
            self.assertEqual(tomllib.load(f)["project"]["version"], EXPECTED)

    def test_dunder_version(self):
        self.assertEqual(layerlong.__version__, EXPECTED)

    def test_site_json_content_version(self):
        site = json.loads((REPO / "web" / "site.json").read_text(encoding="utf-8"))
        self.assertEqual(site["content_version"].lstrip("v"), EXPECTED)

    def test_changelog_current_section(self):
        text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## [{EXPECTED}]", text)
        self.assertIn("[Unreleased]: https://github.com/SuperMarioYL/layerlong/compare/v0.3.0...HEAD", text)
        self.assertIn(f"[{EXPECTED}]: https://github.com/SuperMarioYL/layerlong/releases/tag/v0.3.0", text)

    def test_web_app_version_follows_package(self):
        from layerlong.web import app

        self.assertEqual(app.version, layerlong.__version__)


if __name__ == "__main__":
    unittest.main()
