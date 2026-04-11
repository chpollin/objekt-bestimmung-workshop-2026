# Daten-Bestandsaufnahme

Stand: 2026-04-11. Wird in M1 nach Selektion und in M3 nach Akkuranz-Auswertung aktualisiert.

## Quelle

**Datei:** [`data/Trainingsobjekte_LandNOE_VK.xlsx`](../data/Trainingsobjekte_LandNOE_VK.xlsx) (ein Tabellenblatt).

**Herkunft:** Volkskundliche Sammlung der Landessammlungen Niederösterreich. Auszug aus dem Sammlungsmanagementsystem, vom Workshop-Auftraggeber bereitgestellt. **Urheberrechtlich geschützt** — keine Weiterverbreitung außerhalb des Workshop-Kontexts.

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

**Konsequenz für die UI:** `Medium`, `Dimensions`, `Dated` dürfen nie als Pflichtfelder angenommen werden — der Editor muss leere Werte sauber darstellen.

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
2. **Beschreibungstexte fehlen vollständig.** Die Excel hat keine Spalte mit Katalogtext. Quelle: Detailseite jedes Objekts unter `https://online.landessammlungen-noe.at/objects/{ObjectID}`. Diese Texte sind im präzisen, lakonischen Sammlungsstil und werden in M1 von `scripts/03_scrape_originals.py` einmalig geholt — sowohl als Ground-Truth für den Vergleich mit der KI als auch als Few-Shot-Material für die Prompts.
3. **Zwischenebenen ohne Namen.** Die Excel führt nur Top (Tiefe 2) und Leaf (Tiefe 3/4). Die Mittel-Knoten zwischen `AUT.AAW.AAH` und `AUT.AAW.AAH.AAN.AAD` haben keine eigenen Term-Einträge. Konsequenz: Der Thesaurus-Tree im UI zeigt Mittelknoten mit ihrem CN-Code, nicht klickbar für Filter.

## Externe Quellen

- **Onlinesammlung NÖ**: <https://online.landessammlungen-noe.at>
  - Objektseite (HTML, server-rendered): `/objects/{ObjectID}`
  - **Objekt-JSON-Endpoint**: `/objects/{ObjectID}/json` — liefert ein sauberes Label/Value-Schema. Verifizierte Felder: `title`, `invno`, `description`, `medium`, `dimensions`, `classification` (= Bereich), `thesconceptsKlassifizierung`, `primaryMedia`, `license`, `isShownAt`. Wir nutzen den JSON-Endpoint, **nicht** HTML-Scraping.
  - Bild-Dispatcher: `/internal/media/dispatcher/{MediaID}` (sendet **kein** `Access-Control-Allow-Origin` — siehe ADR-1)
  - Klassifikations-Suchseite listet die 21 Volkskunde-Bereiche auf

## Lizenz der Daten

Auf jedem Objekt-JSON ist ein `license`-Feld. Stichproben zeigen **CC BY-NC 4.0** (`https://creativecommons.org/licenses/by-nc/4.0/`). Das heißt: Nutzung mit Namensnennung und nicht-kommerziell ist erlaubt — der Workshop und das Repo erfüllen das. Im README ist eine entsprechende Attribution Pflicht.

## Wird in M1 ergänzt

- Konkrete Selektions-Statistik der ~250 kuratierten Objekte (aus `scripts/selection_report.txt`)
- Liste der finalen 20 Top-Bereich-Namen (aus `scripts/cache/top_names.json`)
- Scraping-Erfolgsrate der Originalbeschreibungen (aus `scripts/scrape_report.txt`)
- Tatsächliche Repo-Größe der Bilder nach Resize
- Liste der 5 Few-Shot-Beispiele

## Wird in M2/M3 ergänzt

- Tatsächliche Gemini-Kosten und Token-Verbrauch
- Akkuranz: Anteil korrekter Top-Bereich-Wahl, Anteil korrekter Leaf-Term-Wahl, Top-5-Verwechslungen

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
│  scripts/07_judge_sample     → ai_judge.json   │
└────────┬───────────────────────────────────────┘
         │ Commit JSON + Bilder
         ▼
┌────────────────────────────────────────────────┐
│ Static Site (Vanilla, GitHub Pages)            │
│  index.html ◀─ data/json/thesaurus.json        │
│  app.js     ◀─ data/json/objects.json          │
│             ◀─ data/json/originals.json        │
│             ◀─ data/json/ai_blind.json         │
│             ◀─ data/json/ai_enriched.json      │
│             ◀─ data/json/ai_judge.json         │
│             ◀─ data/json/edits.json            │
└────────┬───────────────────────────────────────┘
         │ Experte editiert
         ▼
┌──────────────────────────────┐
│ localStorage (browser)       │
└────────┬─────────────────────┘
         │ Export-Button
         ▼
┌──────────────────────────────┐
│ edits.json (Download)        │
└────────┬─────────────────────┘
         │ git commit + push
         ▼
       Git-Verlauf = Korrektur-Historie
```

## Komponenten-Inventar

| Pfad | Status | Zweck |
|------|--------|-------|
| `data/Trainingsobjekte_LandNOE_VK.xlsx` | M0 | Quelle, nicht verändern |
| `knowledge/README.md`, `requirements.md`, `data.md`, `journal.md`, `sample_iteration.md`, `workflows.md` | M1 | Knowledge-Basis |
| `scripts/_paths.py` | M1 | Zentrale Pfad-Konstanten |
| `scripts/_common.py` | M1 | Geteilte Helper (HTTP, JSON I/O, Logging, .env-Loader) |
| `scripts/01_build_thesaurus.py` | M1 | Thesaurus-Baum + Top-Bereich-Scrape |
| `scripts/02_select_objects.py` | M1 | ~250 Auswahl, stratifiziert |
| `scripts/03_scrape_originals.py` | M1 | Beschreibungstexte + Few-Shot-Auswahl |
| `scripts/04_download_images.py` | M1 | Bilder lokal, resized |
| `scripts/05_preview_selection.py` | M1 | preview.html für visuelles Review |
| `scripts/06_run_gemini.py` | M2 | Gemini-Calls, beide Modi via `--mode` |
| `scripts/_gemini_client.py` | M2 | Geteilte Gemini-Logik (Stage 1+2, Disambiguation) |
| `scripts/07_judge_sample.py` | M2 | LLM-as-a-Judge gegen blind+enriched |
| `scripts/prompts/system_blind.txt` | M2 | System-Prompt blind |
| `scripts/prompts/system_enriched.txt` | M2 | System-Prompt enriched |
| `scripts/prompts/system_judge.txt` | M2 | System-Prompt judge |
| `scripts/prompts/few_shot_examples.json` | M1 (von 03 erzeugt) | 5 echte Katalogbeispiele |
| `data/json/thesaurus.json` + `thesaurus_flat.json` | M1 | Browser + Prompt |
| `data/json/objects.json` | M1 | Master-Metadaten |
| `data/json/originals.json` | M1 | Beschreibungstexte aus Onlinesammlung |
| `data/json/ai_blind.json`, `ai_enriched.json` | M2 | KI-Outputs |
| `data/json/ai_judge.json` | M2 | Judge-Bewertungen |
| `data/json/edits.json` | M3 (vom Tool exportiert) | Experten-Korrekturen |
| `assets/img/*.jpg` | M1 | ~250 Bilder, ≤1024 px |
| `index.html`, `style.css`, `app.js` | M3 | Browser-Tool |
| `design.md` | M3 | UI-Spezifikation |
| `ReadMe.md` | M3 | DE+EN, Urheberrecht |

## Verifikation

**Pipeline (M1+M2):**

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
python 07_judge_sample.py
```

Erwartung: alle ~250 Objekte haben Bild + zwei KI-Outputs + Judge-Bewertung. Selection-Report zeigt sinnvolle Streuung.

**Browser-Tool (M3):**

- `python -m http.server 8000` im Repo-Root
- Filter-Stichprobe: Top-Bereich „Religion und Glaube" anklicken → nur Religions-Objekte sichtbar
- Freitext „Beutel" → Treffer
- Status-Filter „Konflikt" → nur KI-Original-Differenzen
- Klick auf Objekt → Drawer mit Foto + drei Varianten + Judge
- Editor: Beschreibung ändern → Speichern → Status wechselt zu 🟢
- „Bearbeitungen exportieren" → JSON-Datei herunterladbar
- Datei nach `data/json/edits.json` legen, Seite neu laden → Änderung bleibt

**GitHub Pages (M3):**

- Repo auf `main` pushen, Pages aktivieren
- Live-URL aufrufen, gleiche Stichproben wie oben
- Repo-Größe < 100 MB sicherstellen (Stand M1: 17 MB Bilder)

**Workshop-Tag-Test (19.04.2026):**

- Site offline aufrufen (Internet aus). Muss vollständig funktionieren.
