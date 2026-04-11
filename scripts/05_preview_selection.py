"""Render a self-contained HTML gallery of the current selection.

Used as a manual review step before running the Gemini pipeline. Open
scripts/preview.html in a browser, scroll through the ~250 objects, and verify
that the selection looks reasonable. If not, adjust 02_select_objects.py and
re-run.

The output is gitignored — it's a working artifact for the developer, not
part of the repo.
"""
from __future__ import annotations

import html
from collections import Counter

from _common import log, read_json
from _paths import (
    OBJECTS_JSON,
    ORIGINALS_JSON,
    PREVIEW_HTML,
    ensure_dirs,
)


def render(objects: list[dict], originals_by_id: dict) -> str:
    by_top: dict[str, list[dict]] = {}
    for obj in objects:
        by_top.setdefault(obj["top_id"], []).append(obj)

    cards = []
    for top_id in sorted(by_top):
        items = by_top[top_id]
        items.sort(key=lambda o: (o["thesaurus_id"], o["object_id"]))
        cards.append(f'<h2>{html.escape(items[0]["thesaurus_path"][1])} <small>({len(items)})</small></h2>')
        cards.append('<div class="grid">')
        for obj in items:
            oid = obj["object_id"]
            orig = originals_by_id.get(oid, {})
            desc = orig.get("description") or "—"
            title = obj.get("object_name") or "?"
            term = obj.get("thesaurus_term") or "?"
            dated = obj.get("dated") or "—"
            local_img = obj["image_local"]
            cards.append(
                f'<figure>'
                f'<img src="../{local_img}" alt="{html.escape(title)}" loading="lazy">'
                f'<figcaption>'
                f'<strong>{html.escape(title)}</strong><br>'
                f'<span class="term">{html.escape(term)}</span><br>'
                f'<span class="dated">{html.escape(dated)}</span><br>'
                f'<span class="desc">{html.escape(desc)}</span>'
                f'</figcaption></figure>'
            )
        cards.append('</div>')

    counts = Counter(o["top_id"] for o in objects)
    summary = ", ".join(f"{k}={v}" for k, v in counts.most_common())

    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Selection Preview — {len(objects)} objects</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 1.5rem; color: #222; }}
  h1 {{ font-size: 1.4rem; }}
  h2 {{ font-size: 1.1rem; margin-top: 2rem; border-bottom: 1px solid #ddd; padding-bottom: 0.3rem; }}
  small {{ color: #888; font-weight: normal; }}
  .summary {{ font-size: 0.85rem; color: #666; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; }}
  figure {{ margin: 0; background: #f7f7f7; border: 1px solid #e0e0e0; padding: 0.5rem; }}
  figure img {{ width: 100%; height: 180px; object-fit: contain; background: #fff; }}
  figcaption {{ font-size: 0.78rem; line-height: 1.3; margin-top: 0.4rem; }}
  .term {{ color: #009b91; }}
  .dated {{ color: #888; }}
  .desc {{ color: #444; display: block; margin-top: 0.2rem; }}
</style>
</head>
<body>
<h1>Selection Preview — {len(objects)} objects</h1>
<p class="summary">{html.escape(summary)}</p>
{''.join(cards)}
</body>
</html>
"""


def main() -> None:
    ensure_dirs()
    objects = read_json(OBJECTS_JSON)
    if objects is None:
        raise SystemExit("objects.json missing — run 02_select_objects.py first")
    originals = read_json(ORIGINALS_JSON) or []
    originals_by_id = {r["object_id"]: r for r in originals}

    PREVIEW_HTML.write_text(render(objects, originals_by_id), encoding="utf-8")
    log(f"wrote {PREVIEW_HTML}")
    log(f"  open file:///{PREVIEW_HTML.as_posix()} in your browser to review")


if __name__ == "__main__":
    main()
