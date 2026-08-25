"""layerlong CLI — render | extract | diff 薄入口。

  layerlong render input.md -o out/ [--platform gzh|xhs] [--prev prev.json]
  layerlong extract text.txt -o out/ [--model mock|deepseek|qwen|glm]
  layerlong diff prev.json curr.json
"""

from __future__ import annotations

import json
from pathlib import Path

import click

from .diff import diff_docs
from .extract import extract
from .models import LayerDoc
from .parser import parse_csv, parse_markdown
from .renderer import render_diff_html, render_html, render_svg

SAMPLE_HINT = "可参考 examples/sample.md"


def _load_doc(path: Path, platform: str) -> LayerDoc:
    """按扩展名加载输入为 LayerDoc。"""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return LayerDoc.model_validate_json(text)
    if path.suffix == ".csv":
        return parse_csv(text, platform=platform)  # type: ignore[arg-type]
    return parse_markdown(text, platform=platform)  # type: ignore[arg-type]


@click.group(help="layerlong — 分层 SVG/HTML 信息长图工具。改一处数据，只重渲一层。")
@click.version_option(package_name="layerlong")
def cli() -> None:
    """layerlong 命令行入口。"""


@cli.command(help="渲染 markdown/CSV/JSON → 分层 SVG/HTML 长图。")
@click.argument("input", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--out", "out", default="out", type=click.Path(path_type=Path), help="输出目录")
@click.option("--platform", type=click.Choice(["gzh", "xhs"]), default="gzh", help="画布预设")
@click.option("--prev", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="前一版 LayerDoc JSON，用于生成 diff")
def render(input: Path, out: Path, platform: str, prev: Path | None) -> None:
    """渲染输入为分层 SVG/HTML 长图，可选生成 per-layer diff。"""
    doc = _load_doc(input, platform)
    out.mkdir(parents=True, exist_ok=True)

    (out / "long.json").write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    (out / "long.svg").write_text(render_svg(doc), encoding="utf-8")
    (out / "long.html").write_text(render_html(doc), encoding="utf-8")

    if prev is not None:
        prev_doc = LayerDoc.model_validate_json(prev.read_text(encoding="utf-8"))
        report = diff_docs(prev_doc, doc)
        (out / "long.diff.html").write_text(render_diff_html(doc, report), encoding="utf-8")
        click.echo(
            f"diff: {report.n_changed} / {len(doc.layers)} 图层变化，"
            f"变化图层 → {report.changed_ids or '（无）'}"
        )

    click.echo(f"已渲染 → {out}/long.svg + long.html" + (" + long.diff.html" if prev else ""))


@cli.command(help="从自由文本一次性抽取结构化草稿（默认 mock，零 API key）。")
@click.argument("input", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--out", "out", default="out", type=click.Path(path_type=Path), help="输出目录")
@click.option("--platform", type=click.Choice(["gzh", "xhs"]), default="gzh", help="画布预设")
@click.option("--model", type=click.Choice(["mock", "deepseek", "qwen", "glm"]), default="mock", help="抽取后端")
def extract_cmd(input: Path, out: Path, platform: str, model: str) -> None:
    """把自由文本一次性抽取为 LayerDoc JSON（作者拥有的已保存源）。"""
    text = input.read_text(encoding="utf-8")
    doc = extract(text, platform=platform, model=model)  # type: ignore[arg-type]
    out.mkdir(parents=True, exist_ok=True)
    (out / "long.json").write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    click.echo(f"已抽取（{model}）→ {out}/long.json，用 `layerlong render` 渲染")


@cli.command(name="diff", help="比较两个 LayerDoc JSON，输出 per-layer 变化集。")
@click.argument("prev", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("curr", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def diff_cmd(prev: Path, curr: Path) -> None:
    """输出 per-layer 变化集（added/removed/changed/unchanged）。"""
    p = LayerDoc.model_validate_json(prev.read_text(encoding="utf-8"))
    c = LayerDoc.model_validate_json(curr.read_text(encoding="utf-8"))
    report = diff_docs(p, c)
    if not report.changes:
        click.echo("无图层。")
        return
    for ch in report.changes:
        click.echo(f"{ch.kind:10s}\t{ch.id}")
    click.echo(f"— {report.n_changed} / {len(c.layers)} 图层变化")


# 让 `layerlong extract` 而非 `layerlong extract-cmd`。
cli.add_command(extract_cmd, name="extract")


if __name__ == "__main__":  # pragma: no cover
    cli()
