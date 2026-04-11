"""Two-stage Gemini client for thesaurus-constrained object analysis.

Why two stages: Gemini's responseSchema enum is limited to ~120 values, but the
thesaurus has more leaves than that. Stage 1 picks the top area from a small
fixed enum (20 values). Stage 2 then picks the leaf term from the dynamic enum
of just-that-top-area's leaves (always under the limit; verified max is 98).
This guarantees every returned thesaurus_id is a real entry — no hallucination,
no post-validation needed. See ADR-2 in knowledge/requirements.md.

Usage:

    client = GeminiClient()
    result = client.analyze(image_path, mode="blind")
    result = client.analyze(image_path, mode="enriched", object_meta={...})

Environment:
    GEMINI_API_KEY  required

The client is stateless beyond config; safe to instantiate once and reuse.
"""
from __future__ import annotations

import datetime as dt
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import google.generativeai as genai

from _common import GeminiCallResult, gemini_generate_json, read_json
from _paths import (
    FEW_SHOT_JSON,
    SYSTEM_BLIND_TXT,
    SYSTEM_ENRICHED_TXT,
    THESAURUS_FLAT_JSON,
    THESAURUS_JSON,
)

DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"
PROMPT_VERSION = "v2.0"


@dataclass
class GeminiClient:
    model_name: str = DEFAULT_MODEL
    max_retries: int = 3

    _top_options: list[dict] = field(default_factory=list, init=False)
    _leaves_by_top: dict[str, list[dict]] = field(default_factory=dict, init=False)
    _siblings_by_leaf: dict[str, list[str]] = field(default_factory=dict, init=False)
    _duplicate_terms: set[str] = field(default_factory=set, init=False)
    _few_shots: list[dict] = field(default_factory=list, init=False)
    _system_blind: str = field(default="", init=False)
    _system_enriched: str = field(default="", init=False)

    def __post_init__(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise SystemExit("GEMINI_API_KEY env var is required")
        genai.configure(api_key=api_key)
        self._load_thesaurus()
        self._load_few_shots()
        self._load_prompts()

    # -----------------------------------------------------------------------
    # Setup
    # -----------------------------------------------------------------------

    def _load_thesaurus(self) -> None:
        tree = read_json(THESAURUS_JSON)
        if tree is None:
            raise SystemExit("thesaurus.json missing — run 01_build_thesaurus.py first")
        flat = read_json(THESAURUS_FLAT_JSON) or []

        self._top_options = [
            {"id": node["id"], "term": node["term"]} for node in tree["children"]
        ]
        self._top_options.sort(key=lambda x: x["term"])

        by_top: dict[str, list[dict]] = {}
        for leaf in flat:
            by_top.setdefault(leaf["top_id"], []).append(
                {"id": leaf["id"], "term": leaf["term"]}
            )
        for top in by_top:
            by_top[top].sort(key=lambda x: x["term"])
        self._leaves_by_top = by_top

        # Disambiguation: 34 leaf-term names occur in multiple mid-level
        # clusters (e.g. "Hilfsgerät" appears 10 times). Without context the
        # model can't tell apart "Hilfsgerät [Tischlerei]" from
        # "Hilfsgerät [Schmiede]". We pre-compute, for each leaf, the names
        # of its mid-level siblings — they describe what the cluster is about
        # (e.g. siblings = "Hobel, Sägen, Werkstatteinrichtung" → tischlerei).
        # Counted in v1 sample run, biggest single source of mis-classification.
        from collections import Counter

        term_counts = Counter(leaf["term"] for leaf in flat)
        self._duplicate_terms = {t for t, n in term_counts.items() if n > 1}

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
        self._siblings_by_leaf = siblings_by_leaf

    def _load_few_shots(self) -> None:
        self._few_shots = read_json(FEW_SHOT_JSON) or []

    def _load_prompts(self) -> None:
        if SYSTEM_BLIND_TXT.exists():
            self._system_blind = SYSTEM_BLIND_TXT.read_text(encoding="utf-8")
        if SYSTEM_ENRICHED_TXT.exists():
            self._system_enriched = SYSTEM_ENRICHED_TXT.read_text(encoding="utf-8")

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def analyze(
        self,
        image_path: Path,
        mode: str,
        object_meta: dict | None = None,
    ) -> dict:
        if mode not in ("blind", "enriched"):
            raise ValueError(f"unknown mode: {mode}")

        image_bytes = image_path.read_bytes()
        started = time.monotonic()

        stage1 = self._stage1_top_area(image_bytes, mode, object_meta)
        top_id = stage1.payload["top_category_id"]
        if top_id not in self._leaves_by_top:
            raise RuntimeError(f"stage1 returned unknown top_id: {top_id}")

        stage2 = self._stage2_leaf_term(image_bytes, mode, top_id, object_meta)

        total_ms = int((time.monotonic() - started) * 1000)

        return {
            "model": self.model_name,
            "mode": mode,
            "prompt_version": PROMPT_VERSION,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "thesaurus_id": stage2.payload["thesaurus_id"],
            "thesaurus_term": self._term_for(stage2.payload["thesaurus_id"]),
            "top_id": top_id,
            "top_term": self._top_term_for(top_id),
            "stage1_reasoning": stage1.payload.get("reasoning", ""),
            "description": stage2.payload.get("description", ""),
            "material": stage2.payload.get("material", ""),
            "technique": stage2.payload.get("technique", ""),
            "dating": stage2.payload.get("dating", ""),
            "confidence_note": stage2.payload.get("confidence_note", ""),
            "tokens_input": stage1.tokens_input + stage2.tokens_input,
            "tokens_output": stage1.tokens_output + stage2.tokens_output,
            "latency_ms": total_ms,
        }

    # -----------------------------------------------------------------------
    # Stages
    # -----------------------------------------------------------------------

    def _stage1_top_area(
        self, image_bytes: bytes, mode: str, object_meta: dict | None
    ) -> GeminiCallResult:
        top_lines = [f"- {opt['id']}: {opt['term']}" for opt in self._top_options]
        prompt_parts = [
            self._system_for(mode),
            "",
            "STUFE 1 — wähle den passenden Top-Bereich aus dieser Liste:",
            "\n".join(top_lines),
            "",
            "Antworte ausschließlich mit JSON gemäß Schema. "
            "`reasoning` ist ein kurzer deutscher Satz, der die Wahl begründet.",
        ]
        if mode == "enriched" and object_meta:
            prompt_parts.append(self._render_object_meta(object_meta))

        schema = {
            "type": "object",
            "properties": {
                "top_category_id": {
                    "type": "string",
                    "enum": [opt["id"] for opt in self._top_options],
                },
                "reasoning": {"type": "string"},
            },
            "required": ["top_category_id", "reasoning"],
        }

        return self._call(prompt_parts, image_bytes, schema)

    def _stage2_leaf_term(
        self,
        image_bytes: bytes,
        mode: str,
        top_id: str,
        object_meta: dict | None,
    ) -> GeminiCallResult:
        leaves = self._leaves_by_top[top_id]
        leaf_lines: list[str] = []
        for l in leaves:
            line = f"- {l['id']}: {l['term']}"
            # If this term name is duplicated elsewhere in the thesaurus, add
            # its mid-cluster siblings so the model can tell apart e.g.
            # "Hilfsgerät [Hobel, Sägen, Werkstatteinrichtung]" (Tischlerei)
            # from "Hilfsgerät [Bohrwerkzeuge, Werkstatteinrichtung]"
            # (Bohrerei). Without this disambiguation, the model has no way
            # to pick the right one.
            if l["term"] in self._duplicate_terms:
                sibs = self._siblings_by_leaf.get(l["id"], [])
                if sibs:
                    sib_str = ", ".join(sibs[:6])
                    line += f"  [Sub-Cluster mit: {sib_str}]"
            leaf_lines.append(line)

        prompt_parts = [
            self._system_for(mode),
            "",
            f"STUFE 2 — Top-Bereich `{top_id}` ({self._top_term_for(top_id)}) ist gewählt.",
            "Wähle aus genau diesen Unterkategorien die passendste:",
            "\n".join(leaf_lines),
            "",
            self._few_shot_block(),
            "",
            "Antworte ausschließlich mit JSON gemäß Schema. Beschreibung im "
            "lakonischen, präzisen Stil eines Sammlungskatalogs (1–3 Sätze). "
            "`confidence_note` benennt ehrlich, was du nicht sicher erkennen kannst.",
        ]
        if mode == "enriched" and object_meta:
            prompt_parts.append(self._render_object_meta(object_meta))

        schema = {
            "type": "object",
            "properties": {
                "thesaurus_id": {
                    "type": "string",
                    "enum": [l["id"] for l in leaves],
                },
                "description": {"type": "string"},
                "material": {"type": "string"},
                "technique": {"type": "string"},
                "dating": {"type": "string"},
                "confidence_note": {"type": "string"},
            },
            "required": ["thesaurus_id", "description", "confidence_note"],
        }

        return self._call(prompt_parts, image_bytes, schema)

    # -----------------------------------------------------------------------
    # Low-level call
    # -----------------------------------------------------------------------

    def _call(self, prompt_parts: list[str], image_bytes: bytes, schema: dict) -> GeminiCallResult:
        model = genai.GenerativeModel(self.model_name)
        contents = [
            {"mime_type": "image/jpeg", "data": image_bytes},
            "\n".join(prompt_parts),
        ]
        return gemini_generate_json(
            model,
            contents,
            schema,
            max_retries=self.max_retries,
            label="gemini",
        )

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _system_for(self, mode: str) -> str:
        if mode == "blind":
            return self._system_blind or self._default_blind_prompt()
        return self._system_enriched or self._default_enriched_prompt()

    def _default_blind_prompt(self) -> str:
        return (
            "Du bist Sammlungsexperte für die volkskundliche Sammlung der "
            "Landessammlungen Niederösterreich. Du siehst nur das Foto eines "
            "Sammlungsobjekts und bestimmst, was es ist."
        )

    def _default_enriched_prompt(self) -> str:
        return (
            "Du bist Sammlungsexperte für die volkskundliche Sammlung der "
            "Landessammlungen Niederösterreich. Du siehst das Foto eines "
            "Sammlungsobjekts UND bestehende Metadaten dazu."
        )

    def _few_shot_block(self) -> str:
        if not self._few_shots:
            return ""
        lines = ["BEISPIELE für den geforderten Beschreibungsstil (echte Katalogtexte):"]
        for ex in self._few_shots:
            lines.append(f'- "{ex["description"]}" ({ex.get("title")} / {ex.get("classification")})')
        return "\n".join(lines)

    def _render_object_meta(self, meta: dict) -> str:
        lines = ["BESTEHENDE METADATEN:"]
        for label, key in [
            ("Objektname", "object_name"),
            ("Material/Technik", "medium"),
            ("Maße", "dimensions"),
            ("Datierung", "dated"),
        ]:
            v = meta.get(key)
            if v:
                lines.append(f"- {label}: {v}")
        lines.append("")
        lines.append(
            "Wichtig: Diese Felder NICHT wörtlich kopieren. Erzeuge eine neue, "
            "fließende Katalogbeschreibung, die Foto und Metadaten zu einem "
            "konsistenten Eintrag verbindet. Wenn du im Foto etwas siehst, das "
            "den Metadaten widerspricht, erwähne das in `confidence_note`."
        )
        return "\n".join(lines)

    def _term_for(self, leaf_id: str) -> str:
        for leaves in self._leaves_by_top.values():
            for leaf in leaves:
                if leaf["id"] == leaf_id:
                    return leaf["term"]
        return leaf_id

    def _top_term_for(self, top_id: str) -> str:
        for opt in self._top_options:
            if opt["id"] == top_id:
                return opt["term"]
        return top_id
