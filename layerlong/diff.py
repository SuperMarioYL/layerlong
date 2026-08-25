"""per-layer diff：两个 LayerDoc → 图层粒度变化集。

diff 按 layer id 配对，比较 data 与 kind。改一个数据点只让映射到它的
图层进入变化集；渲染器据此只重渲变化图层，不再整张重画。

确定性护城河：diff 作用于作者已保存的结构化源（LayerDoc JSON），
不作用于重新抽取——抽取是一次性的。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .models import Layer, LayerDoc

ChangeKind = Literal["added", "removed", "changed", "unchanged"]


class LayerChange(BaseModel):
    """单个图层在两个版本间的变化。"""

    id: str
    kind: ChangeKind
    layer: Layer | None = Field(default=None)
    prev: Layer | None = Field(default=None)

    @property
    def is_changed(self) -> bool:
        return self.kind != "unchanged"


class DiffReport(BaseModel):
    """两个 LayerDoc 之间的完整变化报告。"""

    changes: list[LayerChange] = Field(default_factory=list)

    @property
    def changed_ids(self) -> list[str]:
        return [c.id for c in self.changes if c.is_changed]

    @property
    def added(self) -> list[LayerChange]:
        return [c for c in self.changes if c.kind == "added"]

    @property
    def removed(self) -> list[LayerChange]:
        return [c for c in self.changes if c.kind == "removed"]

    @property
    def changed(self) -> list[LayerChange]:
        return [c for c in self.changes if c.kind == "changed"]

    @property
    def n_changed(self) -> int:
        return len(self.changed_ids)


def diff_docs(prev: LayerDoc, curr: LayerDoc) -> DiffReport:
    """比较两个 LayerDoc，返回 per-layer 变化集。

    配对键是 layer.id。一个图层被视为 changed 当且仅当它的 data 或 kind
    与前一版不同；bbox/坐标变化不计为 changed（排版重排不算语义变化）。
    """
    prev_map = {layer.id: layer for layer in prev.layers}
    curr_map = {layer.id: layer for layer in curr.layers}

    changes: list[LayerChange] = []
    for layer in curr.layers:
        if layer.id not in prev_map:
            changes.append(LayerChange(id=layer.id, kind="added", layer=layer))
        else:
            pl = prev_map[layer.id]
            if layer.data != pl.data or layer.kind != pl.kind:
                changes.append(
                    LayerChange(id=layer.id, kind="changed", layer=layer, prev=pl)
                )
            else:
                changes.append(LayerChange(id=layer.id, kind="unchanged", layer=layer))

    for layer in prev.layers:
        if layer.id not in curr_map:
            changes.append(LayerChange(id=layer.id, kind="removed", prev=layer))

    return DiffReport(changes=changes)


def changed_set(report: DiffReport) -> set[str]:
    """变化图层 id 集合——渲染器据此只高亮/重渲这些图层。"""
    return set(report.changed_ids)
