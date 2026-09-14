# Changelog

本项目的所有重要变更都记录在此文件。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [0.2.0] - 2026-09-15

### Fixed

- **图表条宽按数据渲染**：SVG 导出此前把所有柱条画成固定 60% 宽（与数值无关，随仓示例的 62/28/10 图表会渲出三条等长柱）；HTML 导出对大于 100 的数值全部饱和为 100%。两种导出现在共用同一"相对本图最大值"的比例计算（`chart_bar_pcts`）。
- **图表层高随条目数增长**：图表图层高度此前固定 160px，超过 5 条数据时柱条会压到下一图层内容；现在高度为 `20 + 30×条数`。
- **CLI 坏输入友好报错**：`render --prev` / `diff` / JSON 输入损坏或非 UTF-8 时不再抛出原始 traceback，改为单行中文错误并以退出码 1 结束。
- **CSV 文档标题**：无显式标题的 CSV 此前把首列列头名（如 `label`）当作文档标题；现在库调用回退为 `Untitled`，CLI 路径使用输入文件名。
- **Web 预览补全 m3 diff 闭环**：预览页记住上一次渲染的 markdown，再次渲染时高亮变化图层并在状态行列出变化图层 ID——"粘贴 → 改一数 → 看到 diff → 导出 PNG"全程无需 CLI；PNG 导出始终使用不带高亮的干净 SVG。
- **Web 预览可在全新安装下运行**：starlette 表单解析需要 `python-multipart`，此前未声明依赖导致 `POST /render` 在全新安装下直接报错；现已加入依赖。
- **新增 `layerlong serve`**：实现 web 模块文档承诺的本地预览入口（`--host` / `--port`），此前文档有、命令无。

### Added

- `CHANGELOG.md`（本文件）。
- 版本一致性测试：`VERSION` / `pyproject.toml` / `__version__` / `web/site.json content_version` / CHANGELOG / FastAPI app 版本保持同步，防止未来 bump 漏改任何一处。

## [0.1.0]

首个发布：LayerDoc 数据模型、markdown/CSV 解析、分层 SVG/HTML 渲染、per-layer diff（只重渲变化图层）、mock 抽取与可选国产模型（DeepSeek/Qwen/GLM）抽取、FastAPI 预览页与浏览器侧 PNG 导出。

[Unreleased]: https://github.com/SuperMarioYL/layerlong/compare/v0.2.0...HEAD
[0.1.0]: https://github.com/SuperMarioYL/layerlong/releases/tag/v0.1.0
[0.2.0]: https://github.com/SuperMarioYL/layerlong/releases/tag/v0.2.0
