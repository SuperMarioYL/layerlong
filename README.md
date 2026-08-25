<div align="right"><sub><a href="./README.en.md">English</a>&nbsp;&nbsp;|&nbsp;&nbsp;<b>简体中文</b></sub></div>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/hero-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="./assets/hero-light.svg">
    <img src="./assets/hero-light.svg" width="880" alt="layerlong">
  </picture>
</p>

<p align="center"><sub>面向公众号 / 小红书长图作者的分层 SVG/HTML 长图工具——改一处数据只重渲一层、可 diff，告别整张重画。</sub></p>

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="license"></a>
  <a href="https://github.com/SuperMarioYL/layerlong/releases"><img src="https://img.shields.io/github/v/release/SuperMarioYL/layerlong" alt="release"></a>
  <a href="https://github.com/SuperMarioYL/layerlong/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/SuperMarioYL/layerlong/ci.yml?branch=main&label=CI" alt="CI"></a>
  <img src="https://img.shields.io/badge/python-3.12%2B-blue" alt="python">
  <img src="https://img.shields.io/badge/long--image-layered-0071E3" alt="layered">
</p>

<p align="center"><b>公众号 / 小红书长图改一个数据就要整张重画？layerlong 把扁平 PNG 换成分层 SVG/HTML 长图——改一处数据，per-layer diff 可见，只重渲变化图层，不再整张重画。</b></p>

---

<h2><img src="https://api.iconify.design/tabler:topology-star-3.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 架构</h2>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/atlas-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="./assets/atlas-light.svg">
    <img src="./assets/atlas-light.svg" width="880" alt="架构：markdown/CSV → LayerDoc → 分层 SVG/HTML">
  </picture>
</p>

单 Python 进程：markdown/CSV/文本 → **LayerDoc**（可 diff 的分层长图文档）→ 渲染器产可编辑分层 SVG/HTML（每图层一个可寻址 `<g id>` / `<section id>`）。改一个数据点只影响映射到它的图层，diff 在图层粒度可见，渲染器只重渲变化图层。PNG 由浏览器侧 canvas 完成，避开 cairo 系统依赖。

## 目录

- [为什么做这个](#为什么做这个)
- [安装与快速开始](#安装与快速开始)
- [用法](#用法)
- [演示](#演示)
- [配置](#配置)
- [付费](#付费)
- [路线图](#路线图)
- [许可证](#许可证)

<h2><img src="https://api.iconify.design/tabler:bulb.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 为什么做这个</h2>

公众号与小红书的"信息长图"作者今天拿到手的是一张扁平 PNG——所有图层在导出时被压平。作者发现一个数据写错、或想把标题里的一个数字更新到新一期，必须重新打开 Figma/PS 源文件、手工定位、改完再整张重导出 PNG、重新上传。

layerlong 把长图当作一个带语义区域的分层矢量项目文件：每个标题、数据行、标注都是可寻址图层，能就地改并与上一版对比，不必整张重画。新原语是 **LayerDoc**——一张可编辑、可 diff 的分层长图文档，在任何竞品中都不存在。

<h2><img src="https://api.iconify.design/tabler:rocket.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 安装与快速开始</h2>

```bash
git clone https://github.com/SuperMarioYL/layerlong.git && cd layerlong
pip install -e .
layerlong render examples/sample.md -o out/
```

<details><summary>sample output</summary>

```
已渲染 → out/long.svg + out.html
```

`out/` 里有三件产物：

- `long.svg` — 分层可编辑 SVG（每图层一个 `<g id="...">`）
- `long.html` — 分层 HTML 长图（每图层一个 `<section id="...">`）
- `long.json` — LayerDoc 源（作者拥有、可反复改的资产）

</details>

改一个数据再渲染，加 `--prev` 看 diff：

```bash
sed 's/23.5/31.2/' examples/sample.md > sample_v2.md
layerlong render sample_v2.md -o out2/ --prev out/long.json
# → diff: 1 / 11 图层变化，变化图层 → ['stat-1']
```

<h2><img src="https://api.iconify.design/tabler:terminal-2.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 用法</h2>

`layerlong` 三个子命令：`render` 渲染、`extract` 抽取、`diff` 比对。

**1. 渲染 markdown/CSV/JSON → 分层长图**

```bash
layerlong render examples/sample.md -o out/ --platform gzh
layerlong render data.csv -o out/ --platform xhs
layerlong render long.json -o out/        # 直接渲染已保存的 LayerDoc
```

**2. 改数据后做 per-layer diff（只重渲变化层）**

```bash
layerlong render sample_v2.md -o out2/ --prev out/long.json
# 产出 out2/long.diff.html，仅高亮变化图层
layerlong diff out/long.json out2/long.json
# 输出每图层 added/removed/changed/unchanged
```

**3. 从自由文本一次性抽取结构化草稿（默认 mock，零 API key）**

```bash
layerlong extract raw_text.txt -o draft/ --model mock
# 可选国产模型（自带 key）：--model deepseek|qwen|glm，导出 LAYERLONG_API_KEY
layerlong render draft/long.json -o out/
```

markdown schema 很小：

```
# 主标题                    → title 图层
## 分段                     → section 图层
stat: 标签 | 值 | 单位      → stat 图层（改值只动这一层）
chart: 标签,值; 标签,值;…   → chart 图层（柱状图）
---                         → divider 图层
> 来源/备注                 → annotation 图层
```

<h2><img src="https://api.iconify.design/tabler:photo.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 演示</h2>

<p align="center"><img src="./assets/demo.svg" width="880" alt="演示：扁平 PNG 整张重画 vs 分层 SVG 只重渲一层"></p>

左半 = 扁平 PNG，改一个数据 → 整张闪烁 + "redraw 整张"；右半 = 分层 SVG，同改 → 只有变化图层高亮 + 重渲，"1 layer changed"。layerlong 的护城河是可编辑分层矢量，不是一次性位图。

<h2><img src="https://api.iconify.design/tabler:adjustments.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 配置</h2>

画布预设（v0.1 仅公众号 + 小红书两种 surface）：

| 预设 | `--platform` | 画布宽 | 边距 | 标题安全区 |
|---|---|---|---|---|
| 公众号 | `gzh` | 750 | 40 | 顶部 80px |
| 小红书 | `xhs` | 1080 | 56 | 顶部 120px |

环境变量（仅模型抽取用，mock 无需）：

| 变量 | 含义 |
|---|---|
| `LAYERLONG_API_KEY` | 国产模型 API key（DeepSeek/Qwen/GLM，OpenAI 兼容） |

<h2><img src="https://api.iconify.design/tabler:credit-card.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 付费</h2>

**v0.1 完全免费开源**（OSS）—— mock 抽取后端零 API key，核心 diff / 渲染 / 模板引擎全部开源。护城河是格式所有权（LayerDoc），闭源反弱化网络效应，故核心开源。

付费层在 **v0.2+**（此处显式排除 v0.1，但对商业创作者受众必须有变现故事）：

- **单次无水印高清导出** — ¥9.9/张：免费 Web 预览导出 PNG 带轻微水印 + 限分辨率，正式发公众号前一键解锁该张高清无水印（最低阻力付费门）。
- **高级模板包** — ¥39–99/份：品牌色 / 字体 / Logo 锁定进 LayerDoc 模板，持续获客入口。
- **品牌套件 + 托管** — ¥99/月 或 ¥888/年：品牌锁定 + 无水印高分辨率 PNG 导出。
- **团队计划** — ¥999/月（≤5 席）：多成员共享 LayerDoc 源 + 协作评论。

LayerDoc 源始终存作者本地 / OSS 仓库，托管层只存高级模板与品牌套件配置——规避"把用户内容锁进云"的信任风险。

<h2><img src="https://api.iconify.design/tabler:map-2.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 路线图</h2>

- [x] **m1** 硬编码分层 SVG PoC + per-layer diff（访谈闸口）
- [x] **m2** 渲染器：markdown/CSV → 分层 SVG/HTML + per-layer diff（只重渲变化层）— CLI `layerlong render` 可跑
- [ ] **m3** FastAPI 预览页（粘贴 markdown → 分层长图 → 改一数据 → diff 高亮 → 浏览器侧 PNG 导出）+ 发布到 GitHub / Gitee
- [ ] v0.2 可视化拖拽图层编辑器、模板市场、品牌套件、CLI PNG 导出、多尺寸画布

<h2><img src="https://api.iconify.design/tabler:license.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 许可证</h2>

MIT — 见 [LICENSE](./LICENSE)。欢迎在 [Issues](https://github.com/SuperMarioYL/layerlong/issues) 报 bug / 提模板需求，或直接发 PR。

<p align="center"><sub><a href="./LICENSE">MIT</a> © 2026 SuperMarioYL</sub></p>
