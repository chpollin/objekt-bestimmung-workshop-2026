"""Run Gemini analysis on the selected objects in one of two modes.

Two modes:
- blind:    Image only. Tests "what can the model derive from the photo alone?"
- enriched: Image + existing object metadata. Tests "what does the model add
            when it has the catalog data as context?"

Pipeline contract:
- Reads data/json/objects.json (or sample.json with --sample).
- Reads data/json/originals.json only in enriched mode (for object_meta).
- Writes data/json/ai_blind.json or ai_enriched.json — one record per object,
  resume-friendly: re-running skips objects already present unless --force.

Cost control:
- --limit N stops after N new calls (good for sample/test runs).
- --budget EUR aborts when the running estimate crosses the threshold.

The cost estimator uses a hard-coded per-1k-token rate near the public Gemini
flash-lite price; verify on https://ai.google.dev/pricing before a full run.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from _common import log, read_json, write_json
from _gemini_client import DEFAULT_MODEL, GeminiClient
from _paths import (
    AI_BLIND_JSON,
    AI_ENRICHED_JSON,
    DATA_JSON,
    IMAGES_DIR,
    OBJECTS_JSON,
    ORIGINALS_JSON,
    ensure_dirs,
)

# Rough Gemini flash-lite preview price (USD per 1M tokens). Verify on
# https://ai.google.dev/pricing before a full run.
PRICE_INPUT_PER_MTOK_USD = 0.10
PRICE_OUTPUT_PER_MTOK_USD = 0.40
USD_TO_EUR = 0.92

SAMPLE_OBJECTS = DATA_JSON / "sample.json"
AI_BLIND_SAMPLE = DATA_JSON / "ai_blind_sample.json"
AI_ENRICHED_SAMPLE = DATA_JSON / "ai_enriched_sample.json"


def estimate_cost_eur(tokens_in: int, tokens_out: int) -> float:
    cost_usd = (
        tokens_in / 1_000_000 * PRICE_INPUT_PER_MTOK_USD
        + tokens_out / 1_000_000 * PRICE_OUTPUT_PER_MTOK_USD
    )
    return cost_usd * USD_TO_EUR


def output_path(mode: str, sample: bool) -> Path:
    if sample:
        return AI_BLIND_SAMPLE if mode == "blind" else AI_ENRICHED_SAMPLE
    return AI_BLIND_JSON if mode == "blind" else AI_ENRICHED_JSON


def input_path(sample: bool) -> Path:
    return SAMPLE_OBJECTS if sample else OBJECTS_JSON


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["blind", "enriched"], required=True)
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Use data/json/sample.json and write *_sample.json (for prompt iteration).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after N new calls (skipped objects don't count).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-call Gemini even if a record already exists.",
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=None,
        help="Hard EUR cap. Pipeline aborts when crossed.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini model name (default: {DEFAULT_MODEL}).",
    )
    args = parser.parse_args()

    ensure_dirs()

    objects = read_json(input_path(args.sample))
    if objects is None:
        raise SystemExit(f"{input_path(args.sample)} missing — run prerequisite scripts first")

    out_path = output_path(args.mode, args.sample)
    existing: list[dict] = read_json(out_path) or []
    existing_by_id = {r["object_id"]: r for r in existing}

    originals_by_id: dict[int, dict] = {}
    if args.mode == "enriched":
        originals = read_json(ORIGINALS_JSON) or []
        originals_by_id = {r["object_id"]: r for r in originals}

    client = GeminiClient(model_name=args.model)
    log(f"mode={args.mode}  model={args.model}  input={input_path(args.sample).name}  output={out_path.name}")
    log(f"existing records: {len(existing_by_id)} of {len(objects)}")

    new_calls = 0
    total_in = sum(r.get("tokens_input", 0) for r in existing if r.get("tokens_input"))
    total_out = sum(r.get("tokens_output", 0) for r in existing if r.get("tokens_output"))
    skipped = 0
    failed: list[int] = []

    for i, obj in enumerate(objects, start=1):
        oid = obj["object_id"]

        if oid in existing_by_id and not args.force:
            skipped += 1
            continue

        image_path = IMAGES_DIR / f"{oid}.jpg"
        if not image_path.exists():
            log(f"  {oid}: SKIP (no local image)")
            failed.append(oid)
            continue

        try:
            object_meta = None
            if args.mode == "enriched":
                object_meta = {
                    "object_name": obj.get("object_name"),
                    "medium": obj.get("medium"),
                    "dimensions": obj.get("dimensions"),
                    "dated": obj.get("dated"),
                }
            result = client.analyze(image_path, mode=args.mode, object_meta=object_meta)
        except Exception as e:
            log(f"  {oid}: ERROR {e}")
            failed.append(oid)
            continue

        result["object_id"] = oid
        existing_by_id[oid] = result
        total_in += result["tokens_input"]
        total_out += result["tokens_output"]
        new_calls += 1

        cost = estimate_cost_eur(total_in, total_out)
        log(
            f"  [{new_calls:>3}] {oid} {obj['object_name']:<22.22} "
            f"-> {result['top_id']}/{result['thesaurus_id']} "
            f"  ({result['tokens_input']}+{result['tokens_output']}tok, "
            f"{result['latency_ms']}ms, est. €{cost:.3f} total)"
        )

        # Persist after every call so we never lose progress.
        all_records = sorted(existing_by_id.values(), key=lambda r: r["object_id"])
        write_json(out_path, all_records)

        if args.budget is not None and cost >= args.budget:
            log(f"BUDGET REACHED: €{cost:.3f} >= €{args.budget:.3f} — stopping.")
            break
        if args.limit is not None and new_calls >= args.limit:
            log(f"LIMIT REACHED: {new_calls} new calls — stopping.")
            break

    log("")
    log(f"summary: new={new_calls} skipped={skipped} failed={len(failed)}")
    log(f"tokens: in={total_in:,} out={total_out:,}  est. cost €{estimate_cost_eur(total_in, total_out):.3f}")
    if failed:
        log(f"failed object_ids: {failed}")


if __name__ == "__main__":
    main()
