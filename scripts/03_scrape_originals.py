"""Fetch original catalog descriptions from the online collection's JSON endpoint.

The Excel has no description column. The online collection exposes one cleanly
under /objects/{ObjectID}/json. We fetch one entry per selected object, cache
each response, and at the end pick five well-formed examples to seed the
few-shot block of the Gemini prompts.

Output:
- data/json/originals.json
- scripts/prompts/few_shot_examples.json
- scripts/scrape_report.txt
- scripts/cache/originals/{object_id}.json (one cache file per object)
"""
from __future__ import annotations

import argparse
import datetime as dt
import random
from collections import Counter

from _common import HttpClient, log, read_json, write_json, write_report
from _paths import (
    FEW_SHOT_JSON,
    OBJECTS_JSON,
    ONLINE_BASE,
    ORIGINALS_CACHE_DIR,
    ORIGINALS_JSON,
    SCRAPE_REPORT,
    ensure_dirs,
)

FEW_SHOT_COUNT = 5
FEW_SHOT_SEED = 42


def value(field) -> str | None:
    if not field:
        return None
    v = field.get("value")
    if isinstance(v, list):
        return ", ".join(str(x) for x in v if x)
    if v in (None, ""):
        return None
    return str(v)


def fetch_one(http: HttpClient, object_id: int) -> dict | None:
    cache_file = ORIGINALS_CACHE_DIR / f"{object_id}.json"
    if cache_file.exists():
        return read_json(cache_file)

    url = f"{ONLINE_BASE}/objects/{object_id}/json"
    try:
        resp = http.get(url)
        payload = resp.json()
    except Exception as e:
        log(f"  {object_id} -> error: {e}")
        return None

    obj = (payload.get("object") or [None])[0]
    if not obj:
        log(f"  {object_id} -> empty payload")
        return None

    record = {
        "object_id": object_id,
        "scraped_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "title": value(obj.get("title")),
        "invno": value(obj.get("invno")),
        "description": value(obj.get("description")),
        "medium": value(obj.get("medium")),
        "dimensions": value(obj.get("dimensions")),
        "classification": value(obj.get("classification")),
        "thes_klassifizierung": value(obj.get("thesconceptsKlassifizierung")),
        "primary_media": value(obj.get("primaryMedia")),
        "license": value(obj.get("license")),
    }
    write_json(cache_file, record)
    return record


def pick_few_shots(records: list[dict]) -> list[dict]:
    """Pick well-formed catalog texts as few-shot examples.

    Criteria:
    - Description present, between 30 and 240 characters (avoids one-word stubs
      and walls of text).
    - Spread across different top-area `classification` values.
    """
    candidates = [
        r for r in records
        if r.get("description") and 30 <= len(r["description"]) <= 240
    ]
    rng = random.Random(FEW_SHOT_SEED)
    rng.shuffle(candidates)

    picked: list[dict] = []
    seen_classifications: set[str] = set()
    for r in candidates:
        cls = r.get("classification") or ""
        if cls in seen_classifications:
            continue
        picked.append(
            {
                "object_id": r["object_id"],
                "title": r.get("title"),
                "classification": cls,
                "description": r["description"],
                "medium": r.get("medium"),
            }
        )
        seen_classifications.add(cls)
        if len(picked) >= FEW_SHOT_COUNT:
            break
    return picked


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only scrape the first N objects (debug/sample run).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch even if cached.",
    )
    args = parser.parse_args()

    ensure_dirs()
    objects = read_json(OBJECTS_JSON)
    if objects is None:
        raise SystemExit("objects.json missing — run 02_select_objects.py first")

    if args.limit:
        objects = objects[: args.limit]

    if args.force:
        for f in ORIGINALS_CACHE_DIR.glob("*.json"):
            f.unlink()

    http = HttpClient()
    records: list[dict] = []
    by_class: Counter[str] = Counter()
    errors: list[int] = []

    log(f"scraping {len(objects)} object pages from {ONLINE_BASE}")
    for i, obj in enumerate(objects, start=1):
        oid = obj["object_id"]
        rec = fetch_one(http, oid)
        if rec is None:
            errors.append(oid)
            continue
        records.append(rec)
        by_class[rec.get("classification") or "?"] += 1
        if i % 25 == 0:
            log(f"  progress: {i}/{len(objects)}")

    write_json(ORIGINALS_JSON, records)
    log(f"wrote {ORIGINALS_JSON} ({len(records)} records, {len(errors)} errors)")

    # Drop objects whose JSON endpoint is unavailable so the rest of the
    # pipeline (images, Gemini, frontend) operates on a consistent set.
    # The online collection occasionally returns 200 on the HTML page but 403
    # on /json for individual objects — without a scrapeable description there
    # is no ground truth to compare against, so the object loses its didactic
    # value for the workshop.
    if errors:
        ok_ids = {r["object_id"] for r in records}
        objects_filtered = [o for o in objects if o["object_id"] in ok_ids]
        if len(objects_filtered) != len(objects):
            write_json(OBJECTS_JSON, objects_filtered)
            log(
                f"updated {OBJECTS_JSON}: {len(objects)} -> {len(objects_filtered)} "
                f"(dropped {len(objects) - len(objects_filtered)} unscrapeable)"
            )

    few_shots = pick_few_shots(records)
    write_json(FEW_SHOT_JSON, few_shots)
    log(f"wrote {FEW_SHOT_JSON} ({len(few_shots)} examples)")

    report: list[str] = []
    report.append(f"Scraped {len(records)} of {len(objects)} objects")
    if errors:
        report.append(f"Errors: {len(errors)}")
        for oid in errors:
            report.append(f"  {oid}")
    report.append("")
    report.append("Per classification:")
    for cls, n in by_class.most_common():
        report.append(f"  {n:>4}  {cls}")
    report.append("")
    report.append("Coverage:")
    have_desc = sum(1 for r in records if r.get("description"))
    have_med = sum(1 for r in records if r.get("medium"))
    have_dim = sum(1 for r in records if r.get("dimensions"))
    report.append(f"  description present: {have_desc}/{len(records)}")
    report.append(f"  medium present:      {have_med}/{len(records)}")
    report.append(f"  dimensions present:  {have_dim}/{len(records)}")
    report.append("")
    report.append("Few-shot examples chosen:")
    for fs in few_shots:
        report.append(f"  [{fs['classification']}] {fs['title']}: {fs['description'][:80]}")
    write_report(SCRAPE_REPORT, report)
    log(f"wrote {SCRAPE_REPORT}")


if __name__ == "__main__":
    main()
