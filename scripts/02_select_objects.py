"""Stratified selection of ~250 objects for the workshop demo.

Strategy (see ADR-8 in knowledge/requirements.md):
- Cap per leaf category to spread the selection across as many categories as
  possible. This proves to workshop participants that the model picks from
  hundreds of options, not a handful.
- Quota per top area so every Volkskunde branch is represented.
- Prefer objects with complete metadata (Medium, Dimensions, Dated) — these
  give the enriched-mode prompt the most context to work with.

Output:
- data/json/objects.json
- scripts/selection_report.txt
"""
from __future__ import annotations

import argparse
import random
from collections import Counter, defaultdict

from _common import load_excel, log, read_json, top_id_of, write_json, write_report
from _paths import (
    OBJECTS_JSON,
    SELECTION_REPORT,
    SOURCE_XLSX,
    THESAURUS_FLAT_JSON,
    ensure_dirs,
)

DEFAULT_TARGET = 250
DEFAULT_PER_LEAF_CAP = 3
DEFAULT_MIN_PER_TOP = 5
RANDOM_SEED = 42


def completeness_score(row: dict) -> int:
    """Higher score = more metadata fields populated."""
    score = 0
    if row.get("Medium"):
        score += 1
    if row.get("Dimensions"):
        score += 1
    if row.get("Dated"):
        score += 1
    if row.get("BeginISODate") is not None:
        score += 1
    return score


def select(
    table,
    flat_thesaurus: list[dict],
    target: int,
    per_leaf_cap: int,
    min_per_top: int,
) -> tuple[list[dict], list[str]]:
    """Pick objects, return (selected_objects, report_lines)."""
    rng = random.Random(RANDOM_SEED)

    by_leaf: dict[str, list[dict]] = defaultdict(list)
    for row in table.iter_dicts():
        cn = row.get("CN")
        if not cn or not row.get("ObjectID") or not row.get("URL_Foto"):
            continue
        by_leaf[cn].append(row)

    for cn in by_leaf:
        by_leaf[cn].sort(key=lambda r: (-completeness_score(r), r.get("ObjectID") or 0))

    leaf_to_top = {leaf["id"]: leaf["top_id"] for leaf in flat_thesaurus}

    selected: list[dict] = []
    seen_ids: set[int] = set()
    used_per_leaf: Counter[str] = Counter()
    used_per_top: Counter[str] = Counter()

    def take(row: dict) -> bool:
        oid = row["ObjectID"]
        if oid in seen_ids:
            return False
        cn = row["CN"]
        if used_per_leaf[cn] >= per_leaf_cap:
            return False
        seen_ids.add(oid)
        used_per_leaf[cn] += 1
        used_per_top[leaf_to_top.get(cn, top_id_of(cn))] += 1
        selected.append(row)
        return True

    tops = sorted({leaf_to_top.get(cn, top_id_of(cn)) for cn in by_leaf})
    leaves_by_top: dict[str, list[str]] = defaultdict(list)
    for cn in by_leaf:
        leaves_by_top[leaf_to_top.get(cn, top_id_of(cn))].append(cn)

    for top in tops:
        leaves = leaves_by_top[top][:]
        rng.shuffle(leaves)
        for cn in leaves:
            if used_per_top[top] >= min_per_top:
                break
            for row in by_leaf[cn]:
                if take(row):
                    break

    all_leaves = list(by_leaf.keys())
    rng.shuffle(all_leaves)
    while len(selected) < target:
        progress = False
        for cn in all_leaves:
            if len(selected) >= target:
                break
            for row in by_leaf[cn]:
                if take(row):
                    progress = True
                    break
        if not progress:
            break

    selected.sort(key=lambda r: (leaf_to_top.get(r["CN"], top_id_of(r["CN"])), r["CN"], r["ObjectID"]))

    leaf_to_term: dict[str, dict] = {leaf["id"]: leaf for leaf in flat_thesaurus}

    objects_out: list[dict] = []
    for row in selected:
        cn = row["CN"]
        leaf = leaf_to_term.get(cn)
        oid = row["ObjectID"]
        url_image = row.get("URL_Foto")
        objects_out.append(
            {
                "object_id": oid,
                "object_number": row.get("ObjectNumber"),
                "object_name": row.get("ObjectName"),
                "thesaurus_id": cn,
                "thesaurus_term": row.get("Term"),
                "thesaurus_path": leaf["path"] if leaf else None,
                "top_id": leaf_to_top.get(cn, top_id_of(cn)),
                "medium": row.get("Medium"),
                "dimensions": row.get("Dimensions"),
                "dated": row.get("Dated"),
                "begin_iso": row.get("BeginISODate"),
                "end_iso": row.get("EndISODate"),
                "url_object": row.get("URL_Objekt"),
                "url_image_remote": url_image,
                "image_local": f"assets/img/{oid}.jpg",
            }
        )

    report: list[str] = []
    report.append(f"Selected {len(objects_out)} objects (target {target})")
    report.append(f"Random seed: {RANDOM_SEED}")
    report.append(f"Per-leaf cap: {per_leaf_cap}")
    report.append(f"Min per top: {min_per_top}")
    report.append("")
    report.append("Per top area:")
    for top in sorted(used_per_top, key=lambda t: -used_per_top[t]):
        report.append(f"  {top:<16} {used_per_top[top]:>4}")
    report.append("")
    report.append(f"Distinct leaves used: {len(used_per_leaf)} of {len(by_leaf)}")
    no_dated = sum(1 for o in objects_out if not o["dated"])
    no_dim = sum(1 for o in objects_out if not o["dimensions"])
    no_med = sum(1 for o in objects_out if not o["medium"])
    report.append(f"Without dating:    {no_dated}")
    report.append(f"Without dimensions: {no_dim}")
    report.append(f"Without medium:    {no_med}")

    return objects_out, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=int, default=DEFAULT_TARGET)
    parser.add_argument("--per-leaf-cap", type=int, default=DEFAULT_PER_LEAF_CAP)
    parser.add_argument("--min-per-top", type=int, default=DEFAULT_MIN_PER_TOP)
    args = parser.parse_args()

    ensure_dirs()
    log(f"loading Excel: {SOURCE_XLSX}")
    table = load_excel(SOURCE_XLSX)

    flat = read_json(THESAURUS_FLAT_JSON)
    if flat is None:
        raise SystemExit("thesaurus_flat.json missing — run 01_build_thesaurus.py first")

    objects, report = select(
        table,
        flat,
        target=args.target,
        per_leaf_cap=args.per_leaf_cap,
        min_per_top=args.min_per_top,
    )

    write_json(OBJECTS_JSON, objects)
    log(f"wrote {OBJECTS_JSON} ({len(objects)} objects)")
    write_report(SELECTION_REPORT, report)
    log(f"wrote {SELECTION_REPORT}")
    for line in report:
        log("  " + line)


if __name__ == "__main__":
    main()
