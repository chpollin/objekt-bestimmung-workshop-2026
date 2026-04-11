# Projekt-Knowledge

Wissensbasis von *Objekt-Bestimmung Workshop 2026*. Workshop am 20.04.2026 in Salzburg, Zielgruppe: Museumsfachleute ohne ML-Kenntnisse, Datenbasis: ~250 Objekte aus der volkskundlichen Sammlung der Landessammlungen NÖ.

## Big Picture

Eine zweiteilige Architektur:

1. **Offline-Pipeline** (Python, in `scripts/`) berechnet alle KI-Antworten einmalig vor und legt JSONs unter `data/json/` ab.
2. **Static Site** (Vanilla HTML/CSS/JS, in Repo-Root) liest die JSONs und stellt sie als Browse/Filter/Edit-Tool bereit. Läuft offline und auf GitHub Pages, kein Backend.

Die KI läuft in **drei Workflows**: Blind (nur Foto) → Enriched (Foto + Metadaten) → Judge (stärkere KI bewertet die schwächere). Details in [`workflows.md`](workflows.md).

## Status

- **M1 — Pipeline bis Bilder lokal:** abgeschlossen. Thesaurus, Selektion, Originaltexte, Bilder, Preview.
- **M1.5 — Sample-Iterationsphase:** läuft. v1-Sample-Run ausgewertet (43 % Top-Match blind, 53 % enriched), v2-Prompts mit Disambiguation und Lebenskontext-Hinweis geschrieben, Judge-Skript folgt.
- **M2 — Vollauf:** wartet auf positives Sample-Resultat aus M1.5.
- **M3 — Browser-Tool, README, Release:** offen.

## Reihenfolge zum Einstieg

1. **[requirements.md](requirements.md)** — Was das System macht und warum (FRs, NFRs, ADRs, Out of Scope, Risiken). Single Source of Truth.
2. **[workflows.md](workflows.md)** — Die drei KI-Workflows als Lehrgeschichte.
3. **[data.md](data.md)** — Datenquellen, Statistik, Datenfluss, Komponenten-Inventar, Verifikations-Anleitung.
4. **[journal.md](journal.md)** — Chronologie der substantiellen Entscheidungen (ADR-Log).
5. **[sample_iteration.md](sample_iteration.md)** — Aktives Arbeitstagebuch der Prompt-Iterationen.

## Externe Quellen

- Excel-Quelldaten: [`../data/Trainingsobjekte_LandNOE_VK.xlsx`](../data/Trainingsobjekte_LandNOE_VK.xlsx)
- Onlinesammlung NÖ: <https://online.landessammlungen-noe.at> (CC BY-NC 4.0)
- Workshop-README: [`../ReadMe.md`](../ReadMe.md)
- UI-Designspezifikation: [`../design.md`](../design.md) (M3)
- Pipeline-Anleitung: [`../scripts/README.md`](../scripts/README.md)

## Konvention

Diese Dateien wachsen mit dem Projekt mit. Wenn sich Anforderungen ändern, wird **zuerst** `requirements.md` aktualisiert, **dann** der Code. Das Journal hält fest, *warum* sich etwas geändert hat. `sample_iteration.md` ist das einzige Dokument, das mit jedem Experiment wächst — die anderen sollten stabil bleiben.
