from pathlib import Path
import json
from layerlong.parser import parse_markdown
from layerlong.diff import diff_docs
from layerlong.renderer import render_svg
text=Path('examples/sample.md').read_text()
before=parse_markdown(text);after=parse_markdown(text.replace('23.5','31.2'))
report=diff_docs(before,after)
svg=render_svg(after)
print(json.dumps({'layers':len(after.layers),'changed_ids':report.changed_ids,'unchanged':len(after.layers)-report.n_changed,'svg_produced':svg.lstrip().startswith('<svg')},ensure_ascii=False,indent=2))
