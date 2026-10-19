[简体中文](./README.md) · [Website](https://layerlong.lei6393.com) · [GitHub](https://github.com/SuperMarioYL/layerlong)

<picture>
  <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="./assets/presentation/hero-mobile-dark.svg">
  <source media="(max-width: 600px)" srcset="./assets/presentation/hero-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="./assets/presentation/hero-dark.svg">
  <img src="./assets/presentation/hero-light.svg" width="960" alt="Hero diagram">
</picture>

# layerlong

**Review infographic changes one layer at a time.**

layerlong keeps an infographic as a structured LayerDoc and exports editable SVG and HTML alongside the JSON source.

## Why use it

When a statistic changes, reviewing a flat image gives little indication of what moved. Stable layer IDs let you compare semantic content and keep the source for the next revision.

- **Keep editable source** — LayerDoc JSON survives image export.
- **Compare by layer** — Changes are tied to layer IDs and content.
- **Export vector and HTML** — Use SVG and HTML from the same document.

## Architecture

<picture>
  <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="./assets/presentation/architecture-mobile-dark.svg">
  <source media="(max-width: 600px)" srcset="./assets/presentation/architecture-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="./assets/presentation/architecture-dark.svg">
  <img src="./assets/presentation/architecture-light.svg" width="960" alt="Architecture diagram">
</picture>

Markdown and CSV parsers create LayerDoc objects. The renderer writes SVG and HTML for all layers. diff_docs pairs layers by ID and compares kind/data; a diff view highlights changed layers. The current CLI regenerates complete output files rather than caching only changed render work.

| Component | Responsibility |
| --- | --- |
| `Input parser` | layerlong/parser.py |
| `LayerDoc` | layerlong/models.py |
| `Layer diff` | layerlong/diff.py |
| `SVG / HTML` | layerlong/renderer.py |

## Install and quickstart

Build with the version declared in the repository manifest. Run the example from the repository root.

```bash
git clone https://github.com/SuperMarioYL/layerlong.git
cd layerlong
uv venv .venv
uv pip install --python .venv/bin/python -e .
source .venv/bin/activate
```

Change the bundled sample growth value from 23.5 to 31.2, compute the layer diff and generate SVG in memory.

```bash
.venv/bin/python examples/presentation-demo.py
```

## Recorded demo

<picture>
  <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="./assets/presentation/process-mobile-dark.svg">
  <source media="(max-width: 600px)" srcset="./assets/presentation/process-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="./assets/presentation/process-dark.svg">
  <img src="./assets/presentation/process-light.svg" width="960" alt="Process diagram">
</picture>

The recorded result identifies the changed semantic layer while the other layers remain unchanged.

```text
{
  "layers": 11,
  "changed_ids": [
    "stat-1"
  ],
  "unchanged": 10,
  "svg_produced": true
}
```

The complete command and output are recorded in [docs/demo-results.json](./docs/demo-results.json). Inputs and reproduction code are included in the repository.

## Usage

The CLI exposes the following operations. Commands after the example use your own paths or identifiers.

```bash
layerlong render examples/sample.md -o out/
layerlong render data.csv -o out/ --platform xhs
layerlong diff previous.json current.json
layerlong extract text.txt -o out/ --model mock
```

## Configuration

render accepts Markdown, CSV and LayerDoc JSON. --platform selects gzh or xhs, --out chooses the output directory, and --prev adds a diff HTML view. extract defaults to mock; online extraction requires the selected provider configuration.

## Integrations and responsibilities

<picture>
  <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="./assets/presentation/integrations-mobile-dark.svg">
  <source media="(max-width: 600px)" srcset="./assets/presentation/integrations-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="./assets/presentation/integrations-dark.svg">
  <img src="./assets/presentation/integrations-light.svg" width="960" alt="Integrations diagram">
</picture>

The following routes are implemented in the source. Choose the input that matches your task and keep the resulting artifact with your project.

| Route | Implemented role |
| --- | --- |
| Markdown / CSV | Structured infographic input |
| LayerDoc JSON | Saved editable source |
| SVG / HTML | Layer-addressable exports |
| Diff HTML | Semantic change highlights |

## Limits and next steps

- Coordinate-only layout changes are not counted as semantic changes; diff compares layer kind and data.
- The current CLI rewrites full outputs. A smaller changed-layer count is not evidence of incremental rendering speed.
- The example uses deterministic parsing and does not exercise optional model extraction.

True incremental rendering and broader export validation are future directions. Preserve the saved LayerDoc when editing so comparisons use explicit structured versions.

## License and contributions

See [LICENSE](./LICENSE). When reporting an issue, include a minimal input, the command, and the observed output.

Development: `uv run pytest` runs the test suite (the dev dependency group is declared and syncs into the project venv); or `python -m unittest discover -s tests`.
