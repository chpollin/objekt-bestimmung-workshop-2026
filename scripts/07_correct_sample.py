"""Corrector: das staerkere Modell prueft die Enriched-Antwort und liefert
eine finale, sammlungsreife Fassung fuer die Objekte in sample.json.

Input:
  data/json/sample.json                      (30 Objekte)
  data/json/ai_enriched_sample_v3.json       (Antworten des Arbeitsmodells)
  scripts/prompts/system_corrector.txt       (System-Prompt)

Output:
  data/json/ai_corrected_sample.json         (finale Fassung pro Objekt)

Modell: Gemini 3.1 Pro (staerker als das Arbeitsmodell Flash Lite).
Zweistufig: zuerst Top-Bereich, dann Leaf. Enum-constrained via JSON-Schema.

Aufruf:
  GEMINI_API_KEY=... python scripts/07_correct_sample.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

from google import genai
from google.genai import types

MODEL = "gemini-3.1-pro-preview"
PROMPT_VERSION = "v1.0"

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "data" / "json"
IMAGES_DIR = ROOT / "assets" / "img"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def write_json(p: Path, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def load_thesaurus():
    tree = read_json(DATA_JSON / "thesaurus.json")
    flat = read_json(DATA_JSON / "thesaurus_flat.json") or []
    top_options = sorted(
        [{"id": n["id"], "term": n["term"]} for n in tree["children"]],
        key=lambda x: x["term"],
    )
    leaves_by_top: dict[str, list[dict]] = {}
    for leaf in flat:
        leaves_by_top.setdefault(leaf["top_id"], []).append(
            {"id": leaf["id"], "term": leaf["term"]}
        )
    for top in leaves_by_top:
        leaves_by_top[top].sort(key=lambda x: x["term"])

    term_counts = Counter(leaf["term"] for leaf in flat)
    duplicate_terms = {t for t, n in term_counts.items() if n > 1}

    siblings_by_leaf: dict[str, list[str]] = {}
    cluster_to_terms: dict[str, list[str]] = {}
    for leaf in flat:
        parts = leaf["id"].split(".")
        mid_id = ".".join(parts[:-1]) if len(parts) >= 5 else leaf["id"]
        cluster_to_terms.setdefault(mid_id, []).append(leaf["term"])
    for leaf in flat:
        parts = leaf["id"].split(".")
        mid_id = ".".join(parts[:-1]) if len(parts) >= 5 else leaf["id"]
        sibs = [t for t in cluster_to_terms[mid_id] if t != leaf["term"]]
        siblings_by_leaf[leaf["id"]] = sibs
    return top_options, leaves_by_top, duplicate_terms, siblings_by_leaf


def render_meta(meta: dict) -> str:
    lines = ["METADATEN AUS DEM SAMMLUNGSMANAGEMENT:"]
    for k, v in [
        ("Objektname", meta.get("object_name")),
        ("Material/Technik", meta.get("medium")),
        ("Maße", meta.get("dimensions")),
        ("Datierung", meta.get("dated")),
    ]:
        if v:
            lines.append(f"- {k}: {v}")
    return "\n".join(lines)


def render_enriched(enriched: dict) -> str:
    return (
        "EINORDNUNG DES ARBEITSMODELLS (Gemini 3.1 Flash Lite, enriched):\n"
        f"- Top-Bereich: {enriched.get('top_term','')} "
        f"({enriched.get('top_id','')})\n"
        f"- Unterkategorie: {enriched.get('thesaurus_term','')} "
        f"({enriched.get('thesaurus_id','')})\n"
        f"- Beschreibung: {enriched.get('description','')}\n"
        f"- Konfidenz-Notiz: {enriched.get('confidence_note','')}"
    )


def correct(
    client: genai.Client,
    image_bytes: bytes,
    system_prompt: str,
    top_options: list[dict],
    leaves_by_top: dict[str, list[dict]],
    duplicate_terms: set[str],
    siblings_by_leaf: dict[str, list[str]],
    object_meta: dict,
    enriched: dict,
) -> dict:
    """Zweistufiger Corrector-Call: Stufe 1 Top, Stufe 2 Leaf + Beschreibung."""
    meta_block = render_meta(object_meta)
    enriched_block = render_enriched(enriched)

    # Stufe 1: Top-Bereich
    top_lines = [f"- {o['id']}: {o['term']}" for o in top_options]
    prompt1_parts = [
        system_prompt,
        "",
        meta_block,
        "",
        enriched_block,
        "",
        "STUFE 1 — Waehle den final korrekten Top-Bereich aus dieser Liste:",
        "\n".join(top_lines),
        "",
        "Antworte ausschliesslich im JSON-Schema. `reasoning` ist ein kurzer deutscher Satz, "
        "der die Wahl (und ggf. die Abweichung vom Arbeitsmodell) begruendet.",
    ]

    schema1 = {
        "type": "object",
        "properties": {
            "final_top_id": {
                "type": "string",
                "enum": [o["id"] for o in top_options],
            },
            "reasoning": {"type": "string"},
        },
        "required": ["final_top_id", "reasoning"],
    }

    resp1 = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            "\n".join(prompt1_parts),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema1,
            temperature=0.1,
        ),
    )
    p1 = json.loads(resp1.text)
    top_id = p1["final_top_id"]
    top_reasoning = p1.get("reasoning", "")
    tokens_in1 = resp1.usage_metadata.prompt_token_count
    tokens_out1 = resp1.usage_metadata.candidates_token_count

    # Stufe 2: Leaf + Beschreibung + Korrekturen
    leaves = leaves_by_top[top_id]
    top_term = next(o["term"] for o in top_options if o["id"] == top_id)
    leaf_lines: list[str] = []
    for leaf in leaves:
        line = f"- {leaf['id']}: {leaf['term']}"
        if leaf["term"] in duplicate_terms:
            sibs = siblings_by_leaf.get(leaf["id"], [])
            if sibs:
                line += f"  [Sub-Cluster mit: {', '.join(sibs[:6])}]"
        leaf_lines.append(line)

    prompt2_parts = [
        system_prompt,
        "",
        meta_block,
        "",
        enriched_block,
        "",
        f"STUFE 2 — Top-Bereich `{top_id}` ({top_term}) ist gewaehlt.",
        "Waehle aus genau diesen Unterkategorien die passendste und schreibe die finale Fassung:",
        "\n".join(leaf_lines),
        "",
        "Antworte ausschliesslich im JSON-Schema. Die finale Beschreibung folgt dem lakonischen, "
        "praezisen Stil eines Sammlungskatalogs. `corrections_applied` listet konkret auf, "
        "was du gegenueber der Arbeitsmodell-Fassung geaendert hast (leer, wenn nur Stilschliff). "
        "`curator_review_needed` ist true, wenn die Zuordnung eine Sammlungs-Eigenheit ist, die "
        "aus Foto und Metadaten nicht eindeutig ableitbar waere.",
    ]

    schema2 = {
        "type": "object",
        "properties": {
            "final_thesaurus_id": {
                "type": "string",
                "enum": [leaf["id"] for leaf in leaves],
            },
            "final_description": {"type": "string"},
            "final_confidence_note": {"type": "string"},
            "corrections_applied": {
                "type": "array",
                "items": {"type": "string"},
            },
            "curator_review_needed": {"type": "boolean"},
        },
        "required": [
            "final_thesaurus_id",
            "final_description",
            "final_confidence_note",
            "corrections_applied",
            "curator_review_needed",
        ],
    }

    resp2 = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            "\n".join(prompt2_parts),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema2,
            temperature=0.1,
        ),
    )
    p2 = json.loads(resp2.text)
    leaf_term = next(l["term"] for l in leaves if l["id"] == p2["final_thesaurus_id"])
    tokens_in2 = resp2.usage_metadata.prompt_token_count
    tokens_out2 = resp2.usage_metadata.candidates_token_count

    return {
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "final_top_id": top_id,
        "final_top_term": top_term,
        "final_thesaurus_id": p2["final_thesaurus_id"],
        "final_thesaurus_term": leaf_term,
        "final_description": p2.get("final_description", ""),
        "final_confidence_note": p2.get("final_confidence_note", ""),
        "corrections_applied": p2.get("corrections_applied", []),
        "curator_review_needed": p2.get("curator_review_needed", False),
        "stage1_reasoning": top_reasoning,
        # Fuer Dashboard-Vergleich: welche Einordnung hatte das Arbeitsmodell,
        # das dem Korrektor als Input gezeigt wurde? Das ist nicht immer
        # identisch mit dem state.aiEnrichedById im Frontend (der den Vollauf
        # laedt, nicht den Sample-Lauf) — deshalb hier explizit mitspeichern.
        "input_enriched_top_id": enriched.get("top_id", ""),
        "input_enriched_thesaurus_id": enriched.get("thesaurus_id", ""),
        "tokens_input": tokens_in1 + tokens_in2,
        "tokens_output": tokens_out1 + tokens_out2,
    }


def main() -> None:
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY env var is required")

    sample = read_json(DATA_JSON / "sample.json")
    if not sample:
        raise SystemExit("data/json/sample.json missing")

    enriched_list = read_json(DATA_JSON / "ai_enriched_sample_v3.json") or []
    enriched_by_id = {r["object_id"]: r for r in enriched_list}

    system_prompt = (PROMPTS_DIR / "system_corrector.txt").read_text(encoding="utf-8")
    top_options, leaves_by_top, duplicate_terms, siblings_by_leaf = load_thesaurus()

    client = genai.Client(api_key=api_key)

    out_path = DATA_JSON / "ai_corrected_sample.json"
    results = read_json(out_path) or []
    done_ids = {r["object_id"] for r in results}

    print(f"[corrector] {len(sample)} Objekte, {len(done_ids)} schon da")
    for i, obj in enumerate(sample, 1):
        oid = obj["object_id"]
        if oid in done_ids:
            continue
        img_path = IMAGES_DIR / f"{oid}.jpg"
        if not img_path.exists():
            print(f"  SKIP {oid}: kein Bild")
            continue
        enriched = enriched_by_id.get(oid)
        if not enriched:
            print(f"  SKIP {oid}: keine Enriched-Antwort")
            continue

        img_bytes = img_path.read_bytes()
        meta = {k: obj.get(k) for k in ("object_name", "medium", "dimensions", "dated")}
        try:
            t0 = time.time()
            r = correct(
                client, img_bytes, system_prompt, top_options, leaves_by_top,
                duplicate_terms, siblings_by_leaf, meta, enriched,
            )
            r["object_id"] = oid
            results.append(r)
            dt_s = time.time() - t0
            changed = "CHANGED" if r["final_top_id"] != enriched.get("top_id") else "KEPT "
            review = "REVIEW" if r["curator_review_needed"] else "      "
            print(
                f"  [{i:>2}/{len(sample)}] {oid} {obj['object_name'][:22]:<22} "
                f"-> {r['final_top_id'].split('.')[-1]}/{r['final_thesaurus_id'].split('.')[-1]:<6} "
                f"{changed} {review} "
                f"({r['tokens_input']}+{r['tokens_output']}tok, {dt_s:.1f}s, "
                f"{len(r['corrections_applied'])} corrections)"
            )
            write_json(out_path, results)
        except Exception as e:
            print(f"  ERR {oid}: {e}")

    print(f"done: {len(results)}/{len(sample)}")


if __name__ == "__main__":
    main()
