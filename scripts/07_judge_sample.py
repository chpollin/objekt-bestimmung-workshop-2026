"""LLM-as-a-Judge over the Gemini sample outputs.

For every object in the sample, send the image, the original sammlungs-record,
the blind answer and the enriched answer to a STRONGER model and let it
critique both. The judge does not classify itself — it grades the two answers
and returns concrete prompt-improvement hints.

Why this exists:
- Manual grading doesn't scale.
- A different (stronger) model gives an independent perspective: not a mirror.
- The hints from the judge are the actionable signal for the next prompt
  iteration: instead of guessing what to improve, we count how often each hint
  recurs and address the top-3.

This script reads from data/json/ai_blind_sample.json and ai_enriched_sample.json.
For an iteration comparison (v1 vs v2), pass --suffix _v1 to read the archived
files and write the judge output with the same suffix.

Output:
- data/json/ai_judge_sample.json (or ai_judge_sample_v1.json with --suffix)
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path

import google.generativeai as genai

from _common import gemini_generate_json, log, read_json, write_json
from _paths import (
    DATA_JSON,
    IMAGES_DIR,
    OBJECTS_JSON,
    ORIGINALS_JSON,
    SYSTEM_JUDGE_TXT,
    ensure_dirs,
)

JUDGE_MODEL = "gemini-3.1-pro-preview"
JUDGE_PROMPT_VERSION = "v1.0"

PRICE_INPUT_PER_MTOK_USD = 1.25
PRICE_OUTPUT_PER_MTOK_USD = 5.00
USD_TO_EUR = 0.92


def estimate_cost_eur(tokens_in: int, tokens_out: int) -> float:
    cost_usd = (
        tokens_in / 1_000_000 * PRICE_INPUT_PER_MTOK_USD
        + tokens_out / 1_000_000 * PRICE_OUTPUT_PER_MTOK_USD
    )
    return cost_usd * USD_TO_EUR


JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": [
                "blind_better",
                "enriched_better",
                "both_correct",
                "both_wrong",
                "tie_plausible",
            ],
        },
        "judge_top_id": {
            "type": "string",
            "description": "Top-Bereich-Code (AUT.AAW.XXX), den der Judge selbst gewählt hätte.",
        },
        "is_collection_quirk": {
            "type": "boolean",
            "description": "True, wenn das Original eine sammlungsspezifische Konvention ist, die aus dem Bild allein nicht ableitbar wäre.",
        },
        "description_quality_blind": {
            "type": "integer",
            "description": "Qualitaet der Blind-Beschreibung auf Skala 1 (unbrauchbar) bis 5 (sammlungsreif).",
        },
        "description_quality_enriched": {
            "type": "integer",
            "description": "Qualitaet der Enriched-Beschreibung auf Skala 1 (unbrauchbar) bis 5 (sammlungsreif).",
        },
        "prompt_improvement_hints": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Konkrete, kurze Hinweise (1 Satz), was am System-Prompt von blind oder enriched fehlt oder irreführt.",
        },
        "reasoning": {
            "type": "string",
            "description": "Zwei bis vier Sätze Begründung des Verdicts.",
        },
    },
    "required": [
        "verdict",
        "judge_top_id",
        "is_collection_quirk",
        "description_quality_blind",
        "description_quality_enriched",
        "prompt_improvement_hints",
        "reasoning",
    ],
}


def build_user_prompt(
    sample_obj: dict, original: dict, blind: dict, enriched: dict
) -> str:
    lines = [
        "OBJEKT",
        f"  ID: {sample_obj['object_id']}",
        f"  Inventarnummer: {sample_obj.get('object_number')}",
        f"  Objektname: {sample_obj.get('object_name')}",
        "",
        "ORIGINAL (Sammlung)",
        f"  Top-Bereich: {sample_obj['top_id']}  ({(sample_obj.get('thesaurus_path') or [None,'?'])[1]})",
        f"  Leaf-Term: {sample_obj['thesaurus_id']}  ({sample_obj.get('thesaurus_term')})",
        f"  Beschreibung: {original.get('description', '—')}",
        f"  Material/Technik: {original.get('medium', '—')}",
        f"  Maße: {original.get('dimensions', '—')}",
        f"  Datierung: {sample_obj.get('dated', '—')}",
        "",
        "KI BLIND (Foto allein)",
        f"  Top-Bereich: {blind['top_id']}  ({blind.get('top_term')})",
        f"  Leaf-Term: {blind['thesaurus_id']}  ({blind.get('thesaurus_term')})",
        f"  Beschreibung: {blind.get('description')}",
        f"  Material: {blind.get('material', '—')}",
        f"  Datierung: {blind.get('dating', '—')}",
        f"  Confidence: {blind.get('confidence_note', '—')}",
        "",
        "KI ENRICHED (Foto + Original-Metadaten)",
        f"  Top-Bereich: {enriched['top_id']}  ({enriched.get('top_term')})",
        f"  Leaf-Term: {enriched['thesaurus_id']}  ({enriched.get('thesaurus_term')})",
        f"  Beschreibung: {enriched.get('description')}",
        f"  Confidence: {enriched.get('confidence_note', '—')}",
        "",
        "Bewerte beide Antworten gegen Foto und Original. "
        "Markiere `is_collection_quirk = true`, wenn das Original eine sammlungsspezifische "
        "Konvention ist, die aus dem Bild allein nicht ableitbar waere. "
        "Liste in `prompt_improvement_hints` konkrete Hinweise, was am Prompt fehlt oder "
        "irrefuehrt - z.B. 'Magnet-Effekt zu Handwerk', 'Material-Trigger zu Hauswirtschaft', "
        "'Religions-vs-Bildwerke-Konvention nicht verstanden'. Fasse dich kurz.",
    ]
    return "\n".join(lines)


def judge_one(
    model,
    sample_obj: dict,
    original: dict,
    blind: dict,
    enriched: dict,
    image_bytes: bytes,
) -> tuple[dict, int, int, int]:
    system = SYSTEM_JUDGE_TXT.read_text(encoding="utf-8")
    user_prompt = build_user_prompt(sample_obj, original, blind, enriched)

    contents = [
        {"mime_type": "image/jpeg", "data": image_bytes},
        system + "\n\n" + user_prompt,
    ]
    result = gemini_generate_json(
        model,
        contents,
        JUDGE_SCHEMA,
        max_retries=3,
        label="judge",
    )
    return (
        result.payload,
        result.tokens_input,
        result.tokens_output,
        result.latency_ms,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suffix",
        default="",
        help='File suffix to read/write, e.g. "_v1" to judge the archived v1 outputs.',
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after N new judgements.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-judge even if a record already exists.",
    )
    parser.add_argument(
        "--selection",
        default=None,
        help='Path to a JSON file with an "object_ids" array; only those are judged.',
    )
    parser.add_argument("--model", default=JUDGE_MODEL)
    args = parser.parse_args()

    ensure_dirs()

    blind_path = DATA_JSON / f"ai_blind_sample{args.suffix}.json"
    enriched_path = DATA_JSON / f"ai_enriched_sample{args.suffix}.json"
    if args.selection:
        out_path = DATA_JSON / f"ai_judge_selection{args.suffix}.json"
    else:
        out_path = DATA_JSON / f"ai_judge_sample{args.suffix}.json"

    sample = read_json(DATA_JSON / "sample.json")
    if sample is None:
        raise SystemExit("sample.json missing")
    sample_by_id = {o["object_id"]: o for o in sample}

    if args.selection:
        sel = read_json(Path(args.selection))
        if not sel or "object_ids" not in sel:
            raise SystemExit(f"selection file {args.selection} missing 'object_ids'")
        wanted = set(sel["object_ids"])
        sample = [o for o in sample if o["object_id"] in wanted]
        log(f"selection file filtered sample: {len(sample)} objects")

    blind = read_json(blind_path) or []
    enriched = read_json(enriched_path) or []
    blind_by_id = {r["object_id"]: r for r in blind}
    enriched_by_id = {r["object_id"]: r for r in enriched}

    originals = read_json(ORIGINALS_JSON) or []
    originals_by_id = {r["object_id"]: r for r in originals}

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY env var is required")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(args.model)

    existing = read_json(out_path) or []
    existing_by_id = {r["object_id"]: r for r in existing}

    log(f"judge model={args.model}  blind={blind_path.name}  enriched={enriched_path.name}  out={out_path.name}")
    log(f"existing judge records: {len(existing_by_id)} of {len(sample)}")

    new = 0
    failed: list[int] = []
    total_in = sum(r.get("tokens_input", 0) for r in existing)
    total_out = sum(r.get("tokens_output", 0) for r in existing)

    for sample_obj in sample:
        oid = sample_obj["object_id"]
        if oid in existing_by_id and not args.force:
            continue
        if oid not in blind_by_id or oid not in enriched_by_id:
            log(f"  {oid}: SKIP (missing AI answer)")
            failed.append(oid)
            continue
        image_path = IMAGES_DIR / f"{oid}.jpg"
        if not image_path.exists():
            log(f"  {oid}: SKIP (no local image)")
            failed.append(oid)
            continue

        try:
            payload, tin, tout, latency = judge_one(
                model,
                sample_obj,
                originals_by_id.get(oid, {}),
                blind_by_id[oid],
                enriched_by_id[oid],
                image_path.read_bytes(),
            )
        except Exception as e:
            log(f"  {oid}: ERROR {e}")
            failed.append(oid)
            continue

        record = {
            "object_id": oid,
            "judge_model": args.model,
            "judge_prompt_version": JUDGE_PROMPT_VERSION,
            "judged_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "tokens_input": tin,
            "tokens_output": tout,
            "latency_ms": latency,
            **payload,
        }
        existing_by_id[oid] = record
        new += 1
        total_in += tin
        total_out += tout

        cost = estimate_cost_eur(total_in, total_out)
        log(
            f"  [{new:>3}] {oid} {sample_obj.get('object_name','')[:18]:<18s}  "
            f"verdict={record['verdict']:<16s}  judge_top={record['judge_top_id']}  "
            f"quirk={record['is_collection_quirk']}  "
            f"q_b={record['description_quality_blind']} q_e={record['description_quality_enriched']}  "
            f"({tin}+{tout}tok, {latency}ms, est. €{cost:.3f})"
        )

        sorted_records = sorted(existing_by_id.values(), key=lambda r: r["object_id"])
        write_json(out_path, sorted_records)

        if args.limit is not None and new >= args.limit:
            log(f"LIMIT REACHED: {new}")
            break

    log("")
    log(f"summary: new={new} failed={len(failed)} total_records={len(existing_by_id)}")
    log(f"tokens: in={total_in:,} out={total_out:,}  est. cost €{estimate_cost_eur(total_in, total_out):.3f}")


if __name__ == "__main__":
    main()
