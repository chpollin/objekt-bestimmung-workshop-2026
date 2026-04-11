# Objekt-Bestimmung — Workshop-Demo

**Workshop:** *Kann KI kulturgeschichtliche Objekte bestimmen — und was brauchte es dafür?*
**Ort/Datum:** Salzburg, 20.04.2026
**Zielgruppe:** Museumsfachleute ohne ML-Kenntnisse

---

## English Abstract

Static-site demo and teaching material for a one-day workshop on AI-assisted object classification in ethnographic museum collections. 245 curated objects from the Volkskundliche Sammlung of the Landessammlungen Niederösterreich are classified by Gemini 3.1 Flash-Lite in two modes — **blind** (image only) and **enriched** (image plus existing metadata) — and compared side-by-side with the original catalog record. A handpicked sample of eight cases is additionally reviewed by Gemini 3.1 Pro acting as an LLM-as-a-judge, flagging "collection quirks" where the AI's answer is not wrong but the collection follows an internal convention. The pipeline is precomputed offline; the browser tool is vanilla HTML/CSS/JS, runs fully offline, and is deployable to GitHub Pages without configuration. Data attribution: [Landessammlungen Niederösterreich](https://online.landessammlungen-noe.at), **CC BY-NC 4.0** — code released under the **MIT License**.

---

## Was ist das?

Ein zweiteiliges System aus einer Python-Offline-Pipeline und einem browserbasierten Vergleichs-Viewer. Ziel: Museumsfachleuten ohne ML-Vorwissen zu zeigen, was ein aktueller Vision-LLM aus einem Objektfoto plus Sammlungsmetadaten ableiten kann — und wo die Grenzen liegen. Besonders didaktisch wichtig sind die **Sammlungs-Quirks**: Fälle, in denen die KI-Antwort visuell und sprachlich korrekt ist, aber trotzdem von der Originalzuordnung abweicht, weil die Sammlung eine interne Konvention hat (z.B. *Totschläger* als Fischerei-Zubehör, nicht als Waffe).

Drei parallele Workflows (Details in [`knowledge/workflows.md`](knowledge/workflows.md)):

1. **Blind** — das Modell sieht nur das Foto.
2. **Enriched** — das Modell sieht Foto und bestehende Metadaten (Objektname, Material, Maße, Datierung).
3. **Judge** — ein stärkeres Modell (Gemini 3.1 Pro) bewertet eine handverlesene 8er-Stichprobe der Ergebnisse und markiert Quirks.

Die Architektur ist bewusst pre-computed statt Live-API: Der Bildserver der Landessammlungen NÖ sendet keine CORS-Header, und ein fehlschlagender Live-Call am Workshop-Tag wäre katastrophal. Details zur Begründung stehen in [`knowledge/requirements.md`](knowledge/requirements.md) unter ADR-1.

## Frontend öffnen

**GitHub Pages:** *(URL wird hier eingetragen, sobald Pages aktiviert ist)*

**Lokal:**

```sh
# Im Repo-Root:
python -m http.server 8000
# Dann http://localhost:8000 im Browser öffnen.
```

Alternativ die „Live Server"-Extension in VS Code verwenden. Kein Build-Step, kein `npm install`, keine externen Abhängigkeiten.

## Pipeline reproduzieren

Die Daten-JSONs unter `data/json/` und die Bilder unter `assets/img/` sind bereits committet — die Pipeline muss für den Betrieb der Demo **nicht** laufen. Sie dient der Nachvollziehbarkeit und als Lehrmaterial. Anleitung und Script-Reihenfolge in [`scripts/README.md`](scripts/README.md). Voraussetzungen: Python 3.10+, ein Gemini-API-Key in `.env` im Repo-Root, und `pip install -r scripts/requirements.txt`.

## Projekt-Knowledge

Alle stabilen Entscheidungen, Datenquellen und Anforderungen leben unter [`knowledge/`](knowledge/README.md). Dort findest du auch das chronologische Entscheidungsjournal, das Arbeitstagebuch der Prompt-Iterationen und den Workflow-Guide.

## Urheberrecht und Lizenz

**Daten und Bilder:** Volkskundliche Sammlung der Landessammlungen Niederösterreich, <https://online.landessammlungen-noe.at>, **CC BY-NC 4.0** (Creative Commons Attribution-NonCommercial 4.0 International). Attribution ist Pflicht, kommerzielle Nutzung ausgeschlossen. Die einzelnen `license`-Felder stehen in `data/json/originals.json` pro Objekt.

**Code:** **MIT License.** Der Code dieses Repos ist frei verwendbar und modifizierbar. Die separate Lizenz für Code und Daten bedeutet: Wer den Code übernimmt und mit eigenen Daten benutzt, tut das unter MIT; die Landessammlungs-Daten bleiben unabhängig davon unter CC BY-NC 4.0.

Eine separate `LICENSE`-Datei ist optional und nicht Teil dieses Commits — der Lizenz-Hinweis oben ist die verbindliche Angabe.

## Disclaimer

Dies ist eine Lehr- und Demo-Site für einen einmaligen Workshop-Vortrag, keine Produktivsoftware. Keine Gewähr auf die Richtigkeit der KI-generierten Beschreibungen, Thesaurus-Zuordnungen oder Judge-Urteile. Die Originalklassifikationen der Landessammlungen NÖ sind die einzige belastbare Referenz.
