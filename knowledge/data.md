# Daten-Bestandsaufnahme

Stand: 2026-04-11, nach Vollauf und Frontend-Abschluss.

## Quelle

**Datei:** [`data/Trainingsobjekte_LandNOE_VK.xlsx`](../data/Trainingsobjekte_LandNOE_VK.xlsx) (ein Tabellenblatt).

**Herkunft:** Volkskundliche Sammlung der Landessammlungen Niederösterreich. Auszug aus dem Sammlungsmanagementsystem, vom Workshop-Auftraggeber bereitgestellt. Lizenz der Objekte: **CC BY-NC 4.0**, siehe Sektion *Lizenz der Daten* unten.

## Struktur

Header (Zeile 1) und 10.722 Datenzeilen. 15 Spalten:

| Spalte | Typ | Beispiel | Lückenrate |
|--------|-----|----------|------------|
| `CN` | Thesaurus-Code, hierarchisch | `AUT.AAW.AAQ.AAM` | 0 |
| `PrimaryCNID` | int | `1569199` | 0 |
| `NodeDepth` | int (2/3/4) | `3` | 0 |
| `Term` | menschenlesbarer Begriff (nur Leaf) | `Accessoires` | 0 |
| `TermID` | int | `2062021` | 0 |
| `ObjectID` | int (URL-Schlüssel) | `1177724` | 0 |
| `ObjectNumber` | string | `VK-20440` | 0 |
| `ObjectName` | string | `Beutel` | 0 |
| `Medium` | string | `Stoff, vernäht` | **239** |
| `Dimensions` | string | `H x B x T: 17 x 14,5 cm` | **1.106** |
| `Dated` | string | `1750` / `19. Jh.` | **2.694** |
| `BeginISODate` | int / null | `1750` | hoch |
| `EndISODate` | int / null | `1799` | hoch |
| `URL_Objekt` | URL | `https://online.landessammlungen-noe.at/objects/1177724` | 0 |
| `URL_Foto` | URL | `https://online.landessammlungen-noe.at/internal/media/dispatcher/374605` | **0** (jedes Objekt hat ein Bild) |

**Konsequenz für die UI:** `Medium`, `Dimensions`, `Dated` dürfen nie als Pflichtfelder angenommen werden — die Original-Variant-Card zeigt leere Felder leer an, ohne Fallback-Text.

## Thesaurus-Statistik

- **415 unique Leaf-Codes** (Spalte `CN`).
- **20 Top-Bereiche** unter `AUT.AAW.*`.
- `NodeDepth`-Verteilung der Zeilen: Tiefe 4 → 9.633, Tiefe 3 → 859, Tiefe 2 → 230. Die Mehrheit der Objekte hängt also auf der dritten Unterebene.
- **Größte Top-Bereiche** nach Anzahl Leafs (relevant für Gemini-Enum-Limit ~120):

  | Top-Code | Leafs |
  |----------|-------|
  | `AUT.AAW.AAH` | **98** |
  | `AUT.AAW.AAC` | 45 |
  | `AUT.AAW.AAQ` | 41 |
  | `AUT.AAW.AAD` | 33 |
  | `AUT.AAW.AAK` | 23 |
  | `AUT.AAW.AAB` | 23 |
  | `AUT.AAW.AAS` | 20 |
  | `AUT.AAW.AAR` | 19 |
  | `AUT.AAW.AAP` | 17 |
  | `AUT.AAW.AAT` | 16 |
  | `AUT.AAW.AAN` | 16 |
  | `AUT.AAW.AAJ` | 14 |
  | `AUT.AAW.AAO` | 12 |
  | `AUT.AAW.AAM` | 11 |
  | `AUT.AAW.AAA` | 8 |
  | `AUT.AAW.AAL` | 7 |
  | `AUT.AAW.AAE` | 5 |
  | `AUT.AAW.AAI` | 3 |
  | `AUT.AAW.AAF` | 3 |
  | `AUT.AAW.AAG` | 1 |

- **Maximaler Top-Bereich (98 Leafs) liegt unter dem Gemini-Enum-Limit ~120.** Die zweistufige Constraint-Strategie (siehe ADR-2) ist sicher.

## Bekannte Lücken

1. **Top-Bereich-Namen fehlen.** Im Excel hat nur `AUT.AAW.AAH` (Handwerk/Industrie/Handel) einen menschenlesbaren Term — die anderen 19 Top-Bereiche tragen nur ihren CN-Code. Quelle für die fehlenden Namen: das Feld „Bereich" auf jeder Onlinesammlungs-Detailseite, z.B. „Volkskunde – Kleidung". `scripts/01_build_thesaurus.py` holt sie einmalig pro Top-Bereich von einer Beispielobjektseite und cached sie unter `scripts/cache/top_names.json`.
2. **Beschreibungstexte fehlen vollständig.** Die Excel hat keine Spalte mit Katalogtext. Quelle: Detailseite jedes Objekts unter `https://online.landessammlungen-noe.at/objects/{ObjectID}`. Diese Texte sind im präzisen, lakonischen Sammlungsstil und werden von `scripts/03_scrape_originals.py` einmalig geholt — sowohl als Ground-Truth für den Vergleich mit der KI als auch als Few-Shot-Material für die Prompts.
3. **Zwischenebenen ohne Namen.** Die Excel führt nur Top (Tiefe 2) und Leaf (Tiefe 3/4). Die Mittel-Knoten zwischen `AUT.AAW.AAH` und `AUT.AAW.AAH.AAN.AAD` haben keine eigenen Term-Einträge. Konsequenz: Der Thesaurus-Tree im UI zeigt Mittelknoten mit ihrem CN-Code, nicht klickbar für Filter.

## Externe Quellen

- **Onlinesammlung NÖ**: <https://online.landessammlungen-noe.at>
  - Objektseite (HTML, server-rendered): `/objects/{ObjectID}`
  - **Objekt-JSON-Endpoint**: `/objects/{ObjectID}/json` — liefert ein sauberes Label/Value-Schema. Verifizierte Felder: `title`, `invno`, `description`, `medium`, `dimensions`, `classification` (= Bereich), `thesconceptsKlassifizierung`, `primaryMedia`, `license`, `isShownAt`. Wir nutzen den JSON-Endpoint, **nicht** HTML-Scraping.
  - Bild-Dispatcher: `/internal/media/dispatcher/{MediaID}` (sendet **kein** `Access-Control-Allow-Origin` — siehe ADR-1)
  - Klassifikations-Suchseite listet die 21 Volkskunde-Bereiche auf

## Lizenz der Daten

Auf jedem Objekt-JSON ist ein `license`-Feld. Stichproben zeigen **CC BY-NC 4.0** (`https://creativecommons.org/licenses/by-nc/4.0/`). Das heißt: Nutzung mit Namensnennung und nicht-kommerziell ist erlaubt — der Workshop und das Repo erfüllen das. Im README ist eine entsprechende Attribution Pflicht.

## Selektion und Vollauf (final)

- **245 Objekte** in `data/json/objects.json`, stratifiziert über alle 20 Top-Bereiche. Ursprünglich 246 — Objekt `1168643` wurde nach drei fehlgeschlagenen Bild-Download-Versuchen aus der Selektion entfernt (siehe `scripts/download_report.txt` und Journal-Eintrag *Objekt 1168643 aus dem Scope entfernt*).
- **245 lokale Bilder** unter `assets/img/*.jpg`, resized auf max. 1024 px lange Kante, gesamt **17 MB**. Repo-Gesamtgröße 38 MB — weit unter NFR-4.
- **Scraping der Originaltexte:** `data/json/originals.json` enthält 245 Einträge (Label/Value plus `description`, `classification`, `license`). Details zum Lauf in `scripts/scrape_report.txt`.
- **Top-Bereich-Namen:** 20 menschenlesbare Bezeichner, aus der Onlinesammlung geholt und unter `scripts/cache/top_names.json` gecacht.
- **Few-Shot-Beispiele:** 5 echte Katalogtexte in `scripts/prompts/few_shot_examples.json`, ausgewählt von `03_scrape_originals.py` aus den gescrapten Beschreibungen.
- **Vollauf *nur Foto*** — Workflow A (`data/json/ai_blind.json`, 245 Records, Prompt v2.0, `gemini-3.1-flash-lite-preview`): Top-Bereich 123/245 = **50 %**, Leaf-Term 62/245 = **25 %**.
- **Vollauf *Foto + Metadaten*** — Workflow B (`data/json/ai_enriched.json`, 245 Records, Prompt v2.0, gleiches Modell): Top-Bereich 150/245 = **61 %**, Leaf-Term 85/245 = **35 %**.
- **Korrektur** — Workflow C (`data/json/ai_corrected_sample.json`, 30 Sample-Objekte, `gemini-3.1-pro-preview`): Finale Top-Bereich-Quote 21/30 = **70 %** und finale Leaf-Quote 13/30 = **43 %** (gegenüber 19/30 = 63 % Bereich und 12/30 = 40 % Leaf im Enriched-Modus v3). 4 Bereichs-Änderungen gegenüber der Enriched-Eingabe, davon 2 zum Treffer, 0 schadeten. 24 Objekte mit mindestens einer angewandten Korrektur (`corrections_applied` nicht leer). 9 Objekte als `curator_review_needed = true` geflaggt.

Detaillierte Iterations-Chronik, inkl. Prompt v1 → v2 und Sample-Runs, in [`sample_iteration.md`](sample_iteration.md).

---

## Datenfluss

```
┌──────────────────┐
│ Excel (Quelle)   │ 10.722 Zeilen, im Repo
└────────┬─────────┘
         │
         ▼
┌────────────────────────────────────────────────┐
│ Pipeline (Python, einmalig, offline)           │
│  scripts/01_build_thesaurus  → thesaurus.json  │
│  scripts/02_select_objects   → objects.json    │
│  scripts/03_scrape_originals → originals.json  │
│  scripts/04_download_images  → assets/img/     │
│  scripts/05_preview_selection→ preview.html    │
│  scripts/06_run_gemini       → ai_blind.json   │
│                              → ai_enriched.json│
│  scripts/07_correct_sample   → ai_corrected_   │
│                                sample.json     │
└────────┬───────────────────────────────────────┘
         │ Commit JSON + Bilder
         ▼
┌────────────────────────────────────────────────┐
│ Static Site (Vanilla, GitHub Pages)            │
│  index.html ◀─ data/json/thesaurus.json        │
│  app.js     ◀─ data/json/thesaurus_flat.json   │
│             ◀─ data/json/objects.json          │
│             ◀─ data/json/originals.json        │
│             ◀─ data/json/ai_blind.json         │
│             ◀─ data/json/ai_enriched.json      │
│             ◀─ data/json/ai_corrected.json     │
│             ◀─ data/json/ai_corrected_sample.  │
│                           json (Fallback)      │
│             ◀─ assets/img/*.jpg                │
└────────────────────────────────────────────────┘
```

Der Frontend-Fluss endet hier: Die Site ist ein reiner Read-Only-Vergleichs-Viewer, es gibt keinen Edit-Pfad, kein localStorage, kein Export, keine `edits.json`. Korrekturen an der Originalzuordnung passieren außerhalb des Tools im Sammlungsmanagementsystem. Siehe ADR-14 und Journal-Eintrag *Frontend-Architektur*.

## Komponenten-Inventar

| Pfad | Zweck |
|------|-------|
| `data/Trainingsobjekte_LandNOE_VK.xlsx` | Quelle, nicht verändern |
| `knowledge/README.md`, `requirements.md`, `data.md`, `journal.md`, `sample_iteration.md`, `workflows.md` | Knowledge-Basis |
| `scripts/_paths.py` | Zentrale Pfad-Konstanten |
| `scripts/_common.py` | Geteilte Helper (HTTP, JSON I/O, Logging, `.env`-Loader, `gemini_generate_json`) |
| `scripts/01_build_thesaurus.py` | Thesaurus-Baum + Top-Bereich-Scrape |
| `scripts/02_select_objects.py` | 245 Objekte stratifiziert auswählen |
| `scripts/03_scrape_originals.py` | Beschreibungstexte + Few-Shot-Auswahl |
| `scripts/04_download_images.py` | Bilder lokal, resized |
| `scripts/05_preview_selection.py` | preview.html für visuelles Review |
| `scripts/06_run_gemini.py` | Gemini-Calls, beide Modi via `--mode` |
| `scripts/_gemini_client.py` | Zweistufige Gemini-Logik (Stage 1 + Stage 2 mit Disambiguation) |
| `scripts/07_correct_sample.py` | Korrektor: stärkeres Modell prüft Enriched-Output, liefert finale Fassung mit Korrektur-Spur |
| `scripts/prompts/system_blind.txt` | System-Prompt blind (v3.0) |
| `scripts/prompts/system_enriched.txt` | System-Prompt enriched (v3.0) |
| `scripts/prompts/system_corrector.txt` | System-Prompt Korrektor (v1.0) |
| `scripts/prompts/few_shot_examples.json` | 5 echte Katalogbeispiele |
| `data/json/thesaurus.json` + `thesaurus_flat.json` | Thesaurus für Browser + Prompts |
| `data/json/objects.json` | Master-Metadaten der 245 Objekte |
| `data/json/originals.json` | Beschreibungstexte aus Onlinesammlung |
| `data/json/ai_blind.json`, `ai_enriched.json` | KI-Outputs, je 245 Records |
| `data/json/ai_corrected_sample.json` | 30 Korrektur-Ergebnisse aus dem Sample-Lauf |
| `assets/img/*.jpg` | 245 Bilder, max. 1024 px lange Kante, gesamt 17 MB |
| `index.html`, `style.css`, `app.js` | Vanilla-Browser-Tool, Vergleichs-Viewer |
| `design.md` | UI-Spezifikation im Ist-Stand |
| `README.md` | Repo-Root-README mit EN-Abstract, CC BY-NC 4.0 und MIT-Hinweis |

## Verifikation

**Pipeline:**

```bash
cd scripts
pip install -r requirements.txt
# GEMINI_API_KEY in .env (gitignored) ablegen, _common.py lädt automatisch
python 01_build_thesaurus.py
python 02_select_objects.py
python 03_scrape_originals.py
python 04_download_images.py
python 05_preview_selection.py     # öffnet preview.html im Browser
python 06_run_gemini.py --mode blind
python 06_run_gemini.py --mode enriched
python 07_correct_sample.py
```

Erwartung: alle 245 Objekte haben Bild + zwei KI-Outputs. Der Korrektor läuft auf den 30 Sample-Objekten aus `data/json/sample.json` und erzeugt `data/json/ai_corrected_sample.json` mit 30 Records.

**Browser-Tool:**

- `python -m http.server 8000` im Repo-Root
- Galerie-Header zeigt „245 Objekte · 20 Bereiche · 225 Kategorien"
- Filter-Stichprobe: Top-Bereich „Religion und Glaube" anklicken → nur Religions-Objekte sichtbar
- Freitext „Beutel" → Treffer
- Status-Filter „Konflikt" alleine → nur rote Kacheln; „keine KI" alleine → leere Galerie (alle 245 haben KI-Daten)
- Klick auf Objekt → Detail-Seite (`#/object/:id`) mit Foto, Original, KI blind, KI erweitert, Korrektur. Prev/Next-Buttons navigieren durch die gefilterten Nachbarn, ESC geht zurück.
- Detail-Seite eines Sample-Objekts mit `curator_review_needed = true` (z.B. `#/object/1183673` Totschläger) → gelber Banner „Kuratorische Prüfung empfohlen" auf der Original-Karte sichtbar
- Akkuranz-Dashboard: drei Panels sichtbar (Akkuranz, Verwechslungen, Korrektur-Panel mit finaler Trefferquote und Zahl der für kuratorische Prüfung geflaggten Objekte)

**GitHub Pages:**

- Repo auf `main` pushen, Pages aktivieren
- Live-URL aufrufen, gleiche Stichproben wie oben
- Repo-Größe weit unter NFR-4 (Stand nach Vollauf: 38 MB gesamt, davon 17 MB Bilder)

**Workshop-Tag-Test (19.04.2026):**

- Site offline aufrufen (Internet aus). Muss vollständig funktionieren — keine externen Requests im DevTools Network-Tab.
