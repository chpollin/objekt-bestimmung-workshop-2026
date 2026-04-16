"""Standalone v3 sample runner using the new google.genai SDK.

Erzeugt die Sample-Varianten ai_blind_sample_v3.json und ai_enriched_sample_v3.json,
die als Arbeitsmodell-Input fuer 07_correct_sample.py dienen.

Warum ein separates Skript und nicht 06_run_gemini.py? Das Hauptskript nutzt
noch die deprecated google.generativeai-SDK, die in der aktuellen Umgebung
haengt. Dieses Skript reproduziert die zweistufige Logik von _gemini_client.py
mit der neuen google.genai-SDK und wurde fuer die v3-Prompt-Iteration genutzt.

Aufruf:
  GEMINI_API_KEY=... python scripts/run_v3_sample.py blind
  GEMINI_API_KEY=... python scripts/run_v3_sample.py enriched

Beide Outputs sind gitignored — fuer die Produktion der finalen Korrektur-
Fassung reicht ai_corrected_sample.json.
"""
from __future__ import annotations

import json
import os
import sys
import time
import datetime as dt
from collections import Counter
from pathlib import Path

from google import genai
from google.genai import types

MODEL = "gemini-3.1-flash-lite-preview"
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
    leaves_by_top = {}
    for leaf in flat:
        leaves_by_top.setdefault(leaf["top_id"], []).append(
            {"id": leaf["id"], "term": leaf["term"]}
        )
    for top in leaves_by_top:
        leaves_by_top[top].sort(key=lambda x: x["term"])

    term_counts = Counter(leaf["term"] for leaf in flat)
    duplicate_terms = {t for t, n in term_counts.items() if n > 1}

    siblings_by_leaf = {}
    cluster_to_terms = {}
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


def render_meta(meta):
    lines = ["", "METADATEN AUS DEM SAMMLUNGSMANAGEMENT:"]
    for k, v in [("Objektname", meta.get("object_name")),
                 ("Material/Technik", meta.get("medium")),
                 ("Maße", meta.get("dimensions")),
                 ("Datierung", meta.get("dated"))]:
        if v:
            lines.append(f"- {k}: {v}")
    return "\n".join(lines)


def run_analyze(client, image_bytes, mode, system_prompt, top_options, leaves_by_top,
                duplicate_terms, siblings_by_leaf, few_shots, object_meta=None):
    # Stage 1
    top_lines = [f"- {o['id']}: {o['term']}" for o in top_options]
    prompt1_parts = [
        system_prompt, "",
        "STUFE 1 — wähle den passenden Top-Bereich aus dieser Liste:",
        "\n".join(top_lines), "",
        "Antworte ausschließlich mit JSON gemäß Schema. `reasoning` ist ein kurzer deutscher Satz.",
    ]
    if mode == "enriched" and object_meta:
        prompt1_parts.append(render_meta(object_meta))

    schema1 = {
        "type": "object",
        "properties": {
            "top_category_id": {"type": "string", "enum": [o["id"] for o in top_options]},
            "reasoning": {"type": "string"},
        },
        "required": ["top_category_id", "reasoning"],
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
    top_id = p1["top_category_id"]
    tokens_in1 = resp1.usage_metadata.prompt_token_count
    tokens_out1 = resp1.usage_metadata.candidates_token_count

    # Stage 2
    leaves = leaves_by_top[top_id]
    leaf_lines = []
    for l in leaves:
        line = f"- {l['id']}: {l['term']}"
        if l["term"] in duplicate_terms:
            sibs = siblings_by_leaf.get(l["id"], [])
            if sibs:
                line += f"  [Sub-Cluster mit: {', '.join(sibs[:6])}]"
        leaf_lines.append(line)

    top_term = next(o["term"] for o in top_options if o["id"] == top_id)
    few_shot_lines = ["BEISPIELE (Stil und Detailtiefe der Sammlung):"]
    for ex in few_shots:
        few_shot_lines.append(f"- {ex.get('classification', '')}: {ex.get('description', '')}")

    prompt2_parts = [
        system_prompt, "",
        f"STUFE 2 — Top-Bereich `{top_id}` ({top_term}) ist gewählt.",
        "Wähle aus genau diesen Unterkategorien die passendste:",
        "\n".join(leaf_lines), "",
        "\n".join(few_shot_lines), "",
        "Antworte ausschließlich mit JSON gemäß Schema. Beschreibung im lakonischen, präzisen Stil eines Sammlungskatalogs. `confidence_note` benennt ehrlich, was du nicht sicher erkennen kannst.",
    ]
    if mode == "enriched" and object_meta:
        prompt2_parts.append(render_meta(object_meta))

    schema2 = {
        "type": "object",
        "properties": {
            "thesaurus_id": {"type": "string", "enum": [l["id"] for l in leaves]},
            "description": {"type": "string"},
            "material": {"type": "string"},
            "technique": {"type": "string"},
            "dating": {"type": "string"},
            "confidence_note": {"type": "string"},
        },
        "required": ["thesaurus_id", "description", "confidence_note"],
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
    tokens_in2 = resp2.usage_metadata.prompt_token_count
    tokens_out2 = resp2.usage_metadata.candidates_token_count

    leaf_term = next(l["term"] for l in leaves if l["id"] == p2["thesaurus_id"])

    return {
        "mode": mode,
        "prompt_version": "v3.0",
        "model": MODEL,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "top_id": top_id,
        "top_term": top_term,
        "thesaurus_id": p2["thesaurus_id"],
        "thesaurus_term": leaf_term,
        "stage1_reasoning": p1.get("reasoning", ""),
        "description": p2.get("description", ""),
        "material": p2.get("material", ""),
        "technique": p2.get("technique", ""),
        "dating": p2.get("dating", ""),
        "confidence_note": p2.get("confidence_note", ""),
        "tokens_input": tokens_in1 + tokens_in2,
        "tokens_output": tokens_out1 + tokens_out2,
    }


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "blind"
    assert mode in ("blind", "enriched")

    sample = read_json(DATA_JSON / "sample.json")
    few_shots = read_json(PROMPTS_DIR / "few_shot_examples.json") or []
    system_blind = (PROMPTS_DIR / "system_blind.txt").read_text(encoding="utf-8")
    system_enriched = (PROMPTS_DIR / "system_enriched.txt").read_text(encoding="utf-8")
    system_prompt = system_blind if mode == "blind" else system_enriched

    top_options, leaves_by_top, duplicate_terms, siblings_by_leaf = load_thesaurus()

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    out_path = DATA_JSON / f"ai_{mode}_sample_v3.json"
    results = read_json(out_path) or []
    done_ids = {r["object_id"] for r in results}

    print(f"[v3 {mode}] {len(sample)} Objekte, {len(done_ids)} schon da")
    for i, obj in enumerate(sample, 1):
        oid = obj["object_id"]
        if oid in done_ids:
            continue
        img_path = IMAGES_DIR / f"{oid}.jpg"
        if not img_path.exists():
            print(f"  SKIP {oid}: kein Bild")
            continue
        img_bytes = img_path.read_bytes()
        meta = None
        if mode == "enriched":
            meta = {k: obj.get(k) for k in ("object_name", "medium", "dimensions", "dated")}
        try:
            t0 = time.time()
            r = run_analyze(client, img_bytes, mode, system_prompt, top_options,
                            leaves_by_top, duplicate_terms, siblings_by_leaf, few_shots, meta)
            r["object_id"] = oid
            results.append(r)
            dt_s = time.time() - t0
            print(f"  [{i:>2}/{len(sample)}] {oid} {obj['object_name'][:22]:<22} "
                  f"-> {r['top_id'].split('.')[-1]}/{r['thesaurus_id'].split('.')[-1]:<6} "
                  f"({r['tokens_input']}+{r['tokens_output']}tok, {dt_s:.1f}s)")
            write_json(out_path, results)
        except Exception as e:
            print(f"  ERR {oid}: {e}")

    print(f"done: {len(results)}/{len(sample)}")


if __name__ == "__main__":
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    main()
