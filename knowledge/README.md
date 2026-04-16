# Projekt-Knowledge

Wissensbasis von *Objekt-Bestimmung Workshop 2026*. Workshop am 20.04.2026 in Salzburg, Zielgruppe: Museumsfachleute ohne ML-Kenntnisse, Datenbasis: 245 Objekte aus der volkskundlichen Sammlung der Landessammlungen NÖ.

## Big Picture

Eine zweiteilige Architektur:

1. **Offline-Pipeline** (Python, in `scripts/`) berechnet alle KI-Antworten einmalig vor und legt JSONs unter `data/json/` ab.
2. **Static Site** (Vanilla HTML/CSS/JS, in Repo-Root) liest die JSONs und stellt sie als Browse-/Filter-/Vergleichs-Viewer bereit. Pro Objekt stehen nebeneinander: Original (Sammlungsdaten), Vision-LLM mit nur dem Foto, Vision-LLM mit Foto plus Metadaten und die finale Korrektur-Fassung vom stärkeren Modell. Kein Editor, kein Export — reine Lese-/Vergleichs-Funktion. Läuft offline und auf GitHub Pages, kein Backend.

Das Modell läuft in **drei Workflows**: *Nur Foto* (Vision-LLM mit Bild) → *Foto + Metadaten* (Vision-LLM mit Bild plus Objektname, Material, Maße, Datierung) → *Korrektur* (stärkeres Modell prüft die Enriched-Fassung und erzeugt die finale, sammlungsreife Version). Details in [`workflows.md`](workflows.md).

## Status

- **Pipeline:** abgeschlossen. Thesaurus, Selektion, Originaltexte, Bilder, beide Vollauf-Modi, Korrektur-Sample.
- **Frontend:** funktional abgeschlossen. Hash-Router mit Gallery-Route (`#/`) und Detail-Route (`#/object/:id`), Filter (Thesaurus-Tree, Status, Freitext, klickbare Confusions), Akkuranz-Dashboard, Banner für kuratorische Prüfung.
- **Abschlussphase (12.–19.04.2026):** Knowledge-Korrekturen, README im Repo-Root, GitHub Pages Deployment, Workshop-Tag-Dry-Run am 19.04. Siehe Plan in `~/.claude/plans/zesty-shimmying-treasure.md`.

## Reihenfolge zum Einstieg

1. **[requirements.md](requirements.md)** — Was das System macht und warum (FRs, NFRs, ADRs, Out of Scope, Risiken). Single Source of Truth.
2. **[workflows.md](workflows.md)** — Die drei KI-Workflows als Lehrgeschichte.
3. **[data.md](data.md)** — Datenquellen, Statistik, Datenfluss, Komponenten-Inventar, Verifikations-Anleitung.
4. **[journal.md](journal.md)** — Chronologie der substantiellen Entscheidungen (ADR-Log).
5. **[sample_iteration.md](sample_iteration.md)** — Aktives Arbeitstagebuch der Prompt-Iterationen.

## Externe Quellen

- Excel-Quelldaten: [`../data/Trainingsobjekte_LandNOE_VK.xlsx`](../data/Trainingsobjekte_LandNOE_VK.xlsx)
- Onlinesammlung NÖ: <https://online.landessammlungen-noe.at> (CC BY-NC 4.0)
- Workshop-README: [`../README.md`](../README.md)
- UI-Designspezifikation: [`../design.md`](../design.md)
- Pipeline-Anleitung: [`../scripts/README.md`](../scripts/README.md)

## Konvention

Diese Dateien wachsen mit dem Projekt mit. Wenn sich Anforderungen ändern, wird **zuerst** `requirements.md` aktualisiert, **dann** der Code. Das Journal hält fest, *warum* sich etwas geändert hat. `sample_iteration.md` ist das einzige Dokument, das mit jedem Experiment wächst — die anderen sollten stabil bleiben.
