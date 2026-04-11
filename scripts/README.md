# Pipeline

Offline-Pipeline, die einmalig läuft und alle Daten produziert, die das Browser-Tool später nur noch liest. Hintergrund und Architekturentscheidungen siehe [`../knowledge/requirements.md`](../knowledge/requirements.md), die drei Workflows in [`../knowledge/workflows.md`](../knowledge/workflows.md), die Iterationsgeschichte in [`../knowledge/sample_iteration.md`](../knowledge/sample_iteration.md).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r scripts/requirements.txt
```

Den Gemini-API-Key in eine `.env`-Datei im Repo-Root schreiben (gitignored):

```
GEMINI_API_KEY=...
```

`scripts/_common.py` lädt `.env` automatisch beim Import. Eine bereits gesetzte Umgebungsvariable gewinnt über die Datei, manuelles `export` in der Shell bleibt also möglich.

## Reihenfolge

**M1 — Datenaufbereitung (keine API-Kosten):**

```bash
python scripts/01_build_thesaurus.py     # data/json/thesaurus.json + thesaurus_flat.json
python scripts/02_select_objects.py      # data/json/objects.json + selection_report.txt
python scripts/03_scrape_originals.py    # data/json/originals.json + few_shot_examples.json
python scripts/04_download_images.py     # assets/img/{object_id}.jpg
python scripts/05_preview_selection.py   # scripts/preview.html (gitignored)
```

**M1.5 — Sample-Iterationsphase (Workflows A und B, kleines Budget):**

```bash
python scripts/dev/sample_select.py                    # data/json/sample.json (30 Objekte)
python scripts/06_run_gemini.py --mode blind --sample  # ai_blind_sample.json
python scripts/06_run_gemini.py --mode enriched --sample  # ai_enriched_sample.json
```

**M1.5 — Judge-Phase (Workflow C, nur handverlesene Teilmenge, Pro-Modell):**

```bash
python scripts/07_judge_sample.py --selection data/json/judge_selection.json
```

Die Selection-Datei ist eine handgepflegte Liste von 6–8 Objekten, die didaktisch besonders interessant sind. Siehe die Auswahl-Begründung in `sample_iteration.md`.

**M2 — Vollauf:**

```bash
python scripts/06_run_gemini.py --mode blind       # data/json/ai_blind.json
python scripts/06_run_gemini.py --mode enriched    # data/json/ai_enriched.json
```

Nach jedem Skript:

- die Konsole liest sich wie ein Mini-Report
- die geschriebene Datei zeigt das volle Resultat
- bei 02–04 zusätzlich `scripts/*_report.txt` lesen

## Skripte

| Skript | Zweck | Modell | Resume |
|--------|-------|--------|--------|
| `01_build_thesaurus.py` | Excel → hierarchischer Thesaurus. Holt einmalig die 20 Top-Bereich-Namen vom JSON-Endpoint der Onlinesammlung und cached sie. | — | ja (Cache, `--force`) |
| `02_select_objects.py` | Stratifiziert ~250 Objekte aus 10.722. `--target`, `--per-leaf-cap`, `--min-per-top`. | — | deterministisch (Seed 42) |
| `03_scrape_originals.py` | Holt Originalbeschreibungen vom JSON-Endpoint, erzeugt Few-Shot-Examples. **Filtert Objekte ohne Scrape-Erfolg automatisch aus `objects.json`.** | — | ja (pro-Objekt-Cache, `--force`, `--limit N`) |
| `04_download_images.py` | Lädt Bilder, resized mit Pillow auf max. 1024 px. `--max-edge`, `--quality`. | — | ja (überspringt vorhandene, `--force`) |
| `05_preview_selection.py` | Erzeugt `scripts/preview.html` für visuelles Review der Selektion. | — | rein lesend |
| `06_run_gemini.py` | Zweistufiger Gemini-Call (Top → Leaf) pro Objekt, beide Modi via `--mode`. `--sample`, `--limit N`, `--force`, `--budget EUR`, `--model`. | `gemini-3.1-flash-lite-preview` | ja |
| `07_judge_sample.py` | LLM-as-a-Judge über die Ergebnisse von 06. Bewertet jede Antwort gegen Original und Bild, schlägt Prompt-Verbesserungen vor. `--selection FILE.json`, `--suffix` (für v1/v2-Vergleich), `--limit N`, `--force`. | `gemini-3.1-pro-preview` | ja |
| `dev/sample_select.py` | **Wegwerf-Tool.** Wählt 30 Objekte deterministisch für die Sample-Iterationsphase. Gitignored. | — | deterministisch |

## Geteilte Module

- `_paths.py` — alle Datei-Pfade an einer Stelle
- `_common.py` — HTTP-Client (Retry, User-Agent, polite sleep), JSON I/O, Excel-Loader, Reporting, `.env`-Loader
- `_gemini_client.py` — Geteilte Gemini-Logik: zweistufiger Stage-1/Stage-2-Aufruf, Stage-2-Disambiguation für duplizierte Leaf-Terms (siehe ADR-11), Few-Shot-Einbindung, Prompt-Loader

## Cache, Working Files und Iterationsartefakte

Alles unter `scripts/cache/`, `scripts/dev/`, `scripts/preview.html` und `data/json/*sample*.json`, `data/json/*_v1.json`, `data/json/judge_selection.json` ist gitignored. Bei Bedarf einfach löschen:

```bash
rm -rf scripts/cache scripts/preview.html
rm data/json/*sample*.json data/json/*_v1.json data/json/judge_selection.json
```

## Stateful: was bleibt im Repo, was nicht

| Pfad | Im Repo? | Warum |
|------|----------|-------|
| `data/Trainingsobjekte_LandNOE_VK.xlsx` | ja | Quelle |
| `data/json/thesaurus.json`, `thesaurus_flat.json`, `objects.json`, `originals.json` | ja | M1-Ergebnisse, vom Frontend gelesen |
| `data/json/ai_blind.json`, `ai_enriched.json` | ja (ab M2-Vollauf) | KI-Outputs Workflows A und B |
| `data/json/*sample*.json`, `*_v1.json`, `judge_selection.json`, `ai_judge_selection.json` | nein | Iterationsartefakte, Wegwerf nach M2 |
| `assets/img/*.jpg` | ja | Lokale Bilder, CC BY-NC 4.0, Attribution im ReadMe |
| `scripts/*.py` (außer `dev/`), `scripts/prompts/*` | ja | Code |
| `scripts/dev/*.py` | nein | Wegwerf-Helfer für die Sample-Phase |
| `scripts/cache/`, `scripts/preview.html`, `scripts/*.log` | nein | Working files |
| `.env` | nein | API-Key, niemals committen |
