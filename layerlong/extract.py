"""文本→结构化草稿抽取（一次性）。

默认 mock：零 API key，用启发式把自由文本整理成 markdown 再走 parser。
可选 DeepSeek/Qwen/GLM（OpenAI 兼容客户端）：作者自带 key，一次性产出
作者拥有的结构化源；diff 作用于已保存源，不作用于重新抽取——这保住了
"可 diff、改局部"的确定性护城河。
"""

from __future__ import annotations

import os
import re

from .models import LayerDoc, Platform
from .parser import parse_markdown

# OpenAI 兼容端点（国产模型）。
MODEL_ENDPOINTS: dict[str, tuple[str, str]] = {
    "deepseek": ("https://api.deepseek.com", "deepseek-chat"),
    "qwen": ("https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
    "glm": ("https://open.bigmodel.cn/api/paas/v4", "glm-4-plus"),
}

_EXTRACT_PROMPT = """你是信息长图结构化助手。把下面的自由文本整理成 layerlong 的 markdown schema，
只输出 markdown，不要解释：
- 第一行用 `# ` 作为长图主标题
- 用 `## ` 划分段落
- 数据行用 `stat: 标签 | 值 | 单位`
- 用 `---` 分隔
- 用 `> ` 标注来源/备注

文本：
"""


def extract_mock(text: str, platform: Platform = "gzh") -> LayerDoc:
    """启发式抽取：自由文本 → markdown → LayerDoc。零 API key，确定性。"""
    md_lines: list[str] = []
    title_set = False
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        # 首个短行（≤24 字、非句末标点）作主标题。
        if not title_set and len(s) <= 24 and not s.endswith(("。", ".", "，", "！", "？")):
            md_lines.append(f"# {s}")
            title_set = True
            continue
        # 含"数字 + 单位/百分号"的行当 stat。
        if re.search(r"\d+(\.\d+)?\s*[%％万千亿]?", s) and len(s) <= 40:
            md_lines.append(f"stat: {_heuristic_stat(s)}")
            continue
        # 以「：」结尾或含冒号的结构行当 section。
        if s.endswith(("：", ":")) or ("：" in s and len(s) <= 20):
            md_lines.append(f"## {s.rstrip('：:')}")
            continue
        md_lines.append(s)
    if not title_set:
        md_lines.insert(0, "# 信息长图")
    return parse_markdown("\n".join(md_lines), platform=platform)


def _heuristic_stat(s: str) -> str:
    """尽力把含数字的行拆成 ``label | value | unit``。"""
    m = re.search(r"^(?P<label>.*?)(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[%％万千亿倍元]?)\s*$", s)
    if m:
        label = m.group("label").strip().rstrip("：:，, ")
        return f"{label} | {m.group('value')} | {m.group('unit')}"
    return f"{s} |  | "


def extract_model(
    text: str,
    platform: Platform = "gzh",
    model: str = "deepseek",
    api_key: str | None = None,
) -> LayerDoc:
    """用国产模型（OpenAI 兼容）一次性抽取结构化草稿。需要作者自带 key。"""
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - 开发依赖未装时的清晰报错
        raise RuntimeError(
            "模型抽取需要 openai 包；mock 抽取无需依赖。"
        ) from exc

    base_url, model_name = MODEL_ENDPOINTS.get(model, MODEL_ENDPOINTS["deepseek"])
    key = api_key or os.environ.get("LAYERLONG_API_KEY") or os.environ.get("API_KEY")
    if not key:
        raise RuntimeError(
            f"模型抽取需要 API key：设置环境变量 LAYERLONG_API_KEY。"
            f"（model={model}）"
        )
    client = OpenAI(api_key=key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "你把自由文本整理为信息长图 markdown。"},
            {"role": "user", "content": _EXTRACT_PROMPT + text},
        ],
        temperature=0.2,
    )
    md = resp.choices[0].message.content or ""
    return parse_markdown(md, platform=platform)


def extract(text: str, platform: Platform = "gzh", model: str = "mock", api_key: str | None = None) -> LayerDoc:
    """统一入口：model=mock 走启发式，否则走国产模型。"""
    if model == "mock":
        return extract_mock(text, platform=platform)
    return extract_model(text, platform=platform, model=model, api_key=api_key)
