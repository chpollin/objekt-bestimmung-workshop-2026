"""Build thesaurus tree from the source Excel.

Output:
- data/json/thesaurus.json     hierarchical tree with human-readable top names
- data/json/thesaurus_flat.json flat list [{id, term, path, top_id}]

Top-area names are missing in the Excel for 19 of 20 top categories. We fetch
them once from the online collection's JSON endpoint (one example object per
top category), cache the result under scripts/cache/top_names.json, and reuse it
on subsequent runs. See knowledge/journal.md (2026-04-11 — Datenquelle: JSON-Endpoint).
"""
from __future__ import annotations

import argparse
from collections import defaultdict

from _common import HttpClient, load_excel, log, read_json, top_id_of, write_json
from _paths import (
    ONLINE_BASE,
    SOURCE_XLSX,
    THESAURUS_FLAT_JSON,
    THESAURUS_JSON,
    TOP_NAMES_CACHE,
    ensure_dirs,
)


def fetch_top_name(http: HttpClient, object_id: int) -> str | None:
    """Fetch the human-readable top-area name from a sample object's JSON endpoint."""
    url = f"{ONLINE_BASE}/objects/{object_id}/json"
    try:
        resp = http.get(url)
        payload = resp.json()
        obj = payload["object"][0]
        return (obj.get("classification") or {}).get("value")
    except Exception as e:
        log(f"  fetch_top_name failed for {object_id}: {e}")
        return None


def build_top_names(table, force: bool) -> dict[str, str]:
    """For each top-area code, find one example object and look up its 'classification' (= Bereich)."""
    cached: dict[str, str] = read_json(TOP_NAMES_CACHE, default={}) or {}
    if not force and cached:
        log(f"reusing cached top names ({len(cached)} entries) — pass --force to refresh")
        return cached

    examples: dict[str, int] = {}
    for row in table.rows:
        cn = table.get(row, "CN")
        oid = table.get(row, "ObjectID")
        if not cn or not oid:
            continue
        top = top_id_of(cn)
        examples.setdefault(top, oid)

    log(f"resolving {len(examples)} top-area names from online collection")
    http = HttpClient()
    result: dict[str, str] = dict(cached)
    for top, oid in sorted(examples.items()):
        if not force and top in result:
            continue
        name = fetch_top_name(http, oid)
        if name:
            result[top] = name
            log(f"  {top} -> {name}")
        else:
            log(f"  {top} -> (no name)")
    write_json(TOP_NAMES_CACHE, result)
    return result


def build_tree(table, top_names: dict[str, str]) -> dict:
    """Build a hierarchical tree from CN paths.

    Mid-level nodes (where the Excel has no Term) get their CN code as label.
    The frontend will render those as non-clickable structural nodes.
    """
    nodes: dict[str, dict] = {}
    leaf_terms: dict[str, str] = {}

    for row in table.rows:
        cn = table.get(row, "CN")
        term = table.get(row, "Term")
        if not cn:
            continue
        if term and cn not in leaf_terms:
            leaf_terms[cn] = term

    for cn in sorted(leaf_terms.keys()):
        parts = cn.split(".")
        for depth in range(3, len(parts) + 1):
            node_id = ".".join(parts[:depth])
            if node_id in nodes:
                continue
            if depth == 3:
                # Top-area name always comes from the online collection so all
                # 20 top nodes share the same naming convention. Without this
                # override, AUT.AAW.AAH would keep its Excel term and look
                # different from its 19 siblings.
                term = top_names.get(node_id) or leaf_terms.get(node_id) or node_id
            else:
                term = leaf_terms.get(node_id) or node_id
            nodes[node_id] = {"id": node_id, "term": term, "children": []}

    for node_id, node in nodes.items():
        parts = node_id.split(".")
        if len(parts) <= 3:
            continue
        parent_id = ".".join(parts[:-1])
        parent = nodes.get(parent_id)
        if parent is not None:
            parent["children"].append(node)

    top_nodes = [node for node_id, node in nodes.items() if len(node_id.split(".")) == 3]
    top_nodes.sort(key=lambda n: n["term"])

    def sort_recursive(node: dict) -> None:
        node["children"].sort(key=lambda n: n["term"])
        for child in node["children"]:
            sort_recursive(child)

    for node in top_nodes:
        sort_recursive(node)

    return {"root": "Volkskundliche Sammlung NÖ", "children": top_nodes}


def build_flat(tree: dict) -> list[dict]:
    """Walk the tree and emit a flat list of all leaves with their full path."""
    flat: list[dict] = []

    def visit(node: dict, path: list[str]) -> None:
        new_path = path + [node["term"]]
        if not node["children"]:
            top_id = ".".join(node["id"].split(".")[:3])
            flat.append(
                {
                    "id": node["id"],
                    "term": node["term"],
                    "path": new_path,
                    "top_id": top_id,
                }
            )
        else:
            for child in node["children"]:
                visit(child, new_path)

    for top in tree["children"]:
        visit(top, [tree["root"]])
    return flat


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch top-area names from the online collection even if cached.",
    )
    args = parser.parse_args()

    ensure_dirs()
    log(f"loading Excel: {SOURCE_XLSX}")
    table = load_excel(SOURCE_XLSX)
    log(f"  {len(table.rows)} rows, {len(table.header)} columns")

    top_names = build_top_names(table, force=args.force)

    tree = build_tree(table, top_names)
    write_json(THESAURUS_JSON, tree)
    log(f"wrote {THESAURUS_JSON}")

    flat = build_flat(tree)
    write_json(THESAURUS_FLAT_JSON, flat)
    log(f"wrote {THESAURUS_FLAT_JSON} ({len(flat)} leaves)")

    log(f"top areas: {len(tree['children'])}")
    for top in tree["children"]:
        log(f"  {top['id']:<16} {top['term']}")


if __name__ == "__main__":
    main()
