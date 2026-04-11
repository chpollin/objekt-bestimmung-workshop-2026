# Entscheidungsjournal

Chronologie der substantiellen Projekt-Entscheidungen. Format pro Eintrag:

```
### YYYY-MM-DD — Titel
**Anlass:** ...
**Entscheidung:** ...
**Verworfene Alternativen:** ...
**Konsequenz:** ...
```

---

### 2026-04-11 — Projekt-Setup, Architektur und Knowledge-Basis

**Anlass:** Initiale Projekt-Aufsetzung für den Workshop „Kann KI kulturgeschichtliche Objekte bestimmen?" am 20.04.2026 in Salzburg. Der Auftraggeber stellt 10.722 Objekte der volkskundlichen Sammlung der Landessammlungen NÖ als Excel zur Verfügung. Initial war ein Live-API-Browser-Demo mit Gemini geplant.

**Entscheidung:** Komplett-Pivot auf eine zweiteilige Architektur:

1. **Offline-Pipeline (Python)** in `scripts/` berechnet alle KI-Antworten einmalig vor.
2. **Static Site (Vanilla HTML/CSS/JS)** als Browser-basiertes Review-/Editor-Tool für die KI-Vorschläge.

Beide KI-Modi werden parallel berechnet (blind = nur Foto / enriched = Foto + Original-Metadaten), siehe ADR-3.

Für den Thesaurus-Constraint wird ein zweistufiger Gemini-Call verwendet (Top-Bereich → Leaf), siehe ADR-2. Die Knowledge-Basis lebt unter `knowledge/` im Repo, der Implementierungsplan dagegen in `~/.claude/plans/` als Wegwerf-Werkzeug, siehe ADR-9.

**Verworfene Alternativen:**

- *Live-Browser-API mit User-Key:* Verworfen, weil der Bildserver der Landessammlungen NÖ keine `Access-Control-Allow-Origin`-Header sendet (`curl -I` verifiziert). `<img src>` rendert, aber `fetch()` für Base64-Konvertierung wird vom Browser blockiert. Selbst mit Erlaubnis zur Datennutzung scheitert der Live-Call an der Browser-Security-Policy. Plus: Live-API-Risiko am Workshop-Tag wäre katastrophal.
- *Public CORS-Proxy:* Fragil, externes Risiko.
- *Single Gemini-Call mit responseSchema-Enum über alle 415 Leaf-Terms:* Verworfen wegen Geminis Enum-Limit von ~120 Werten. Verifiziert: Größter Top-Bereich `AUT.AAW.AAH` hat 98 Leafs, also passt jede Stufe-2-Auswahl in ein hartes Enum.
- *Single Call ohne Constraint mit Post-Validierung:* Didaktisch ehrlich, aber Halluzinationsrisiko.
- *Backend (Firebase/Supabase) für Edits:* Overkill für genau einen Experten. Stattdessen: localStorage + Export-JSON + manueller Git-Commit, siehe ADR-5.
- *Plan-Datei als alleinige Doku:* Verworfen, weil der Plan in `~/.claude/plans/` nur lokal sichtbar und vergänglich ist. Anforderungen müssen für andere lesbar sein und mitwachsen — daher `knowledge/requirements.md` als Single Source of Truth.
- *Eigener `pipeline/`-Ordner:* Verworfen, weil das Repo bereits einen leeren `scripts/`-Ordner enthielt. Die existierende Struktur wird respektiert (`scripts/` + `data/json/`), siehe ADR-10.

**Konsequenz:**

- Workshop-Tag-Risiko = 0, weil keine Live-Calls.
- Repo enthält nach M1+M2 alle Bilder (~40 MB) und KI-Outputs deterministisch.
- Knowledge-Basis (`knowledge/{README, requirements, data, journal}.md`) ist die Stelle, wo Anforderungen, Datenwissen und Entscheidungen leben.
- 3-Milestones-Umsetzung: M1 = Pipeline bis Bilder lokal + Knowledge, M2 = Gemini-Calls beider Modi, M3 = Browser-Tool + Release. Jeder Milestone endet mit Refactoring-Slot und Knowledge-Update.

---

### 2026-04-11 — Datenquelle: JSON-Endpoint statt HTML-Scraping

**Anlass:** Vor dem Schreiben von `scripts/03_scrape_originals.py` wurde geprüft, wie die Detailseiten der Onlinesammlung HTML-strukturiert sind. Stichprobe an `/objects/1177724` zeigte server-rendered HTML mit klaren CSS-Klassen (`.detailField`, `.classificationField`), aber im `<head>` wurde ein `<link rel="meta" type="application/json" href="/objects/1177724/json">` entdeckt.

**Entscheidung:** Statt HTML mit BeautifulSoup zu parsen, wird der JSON-Endpoint `/objects/{ObjectID}/json` verwendet. Verifiziert auf drei Stichproben (Beutel, Holznagel, zwei Andachtsbildchen): liefert sauberes Label/Value-Schema mit allen benötigten Feldern (`title`, `description`, `medium`, `dimensions`, `classification`, `primaryMedia`, `license`).

**Verworfene Alternativen:**

- *HTML-Scraping mit BeautifulSoup:* Funktioniert auch (CSS-Klassen vorhanden), aber fragiler gegenüber Layout-Änderungen, mehr Code, kein Vorteil.
- *Headless Browser:* Nicht nötig, weil server-rendered.

**Konsequenz:**

- `scripts/03_scrape_originals.py` parst nur JSON, kein HTML.
- `scripts/01_build_thesaurus.py` holt die Top-Bereich-Namen ebenfalls über den JSON-Endpoint (Feld `classification`), nicht über Webseiten.
- Auf jedem Objekt ist ein `license`-Feld; Stichproben zeigen **CC BY-NC 4.0**. Das ändert die README-Story: Daten sind unter CC BY-NC 4.0 nutzbar (Namensnennung + nicht-kommerziell), nicht „nur Workshop unter Genehmigung". Attribution im README ist Pflicht.
- Die `beautifulsoup4`-Dependency in `scripts/requirements.txt` wird unnötig — Python `json` reicht.

---

### 2026-04-11 — Sample-First-Workflow eingefügt zwischen M1 und M2

**Anlass:** Vor dem Gemini-Vollauf auf 246 Objekte × 2 Modi (= 492 Calls) gibt es zu viele Unbekannte: Wie gut ist Prompt v1? Wie groß ist die Akkuranz-Lücke zwischen blind und enriched? Welche Top-Bereiche sind systematisch schwierig? Ohne Antworten würden wir ggf. Stunden/Cents in einen Vollauf stecken, der danach komplett neu gemacht werden müsste.

**Entscheidung:** Eine **Sample-Iterationsphase** einfügen:

1. 30 Sample-Objekte deterministisch wählen (`scripts/sample_select.py`, gitignored), gestreut über alle 20 Top-Bereiche, mit Bonus für Mismatch-Fälle, in denen ObjectName und Leaf-Term semantisch auseinanderlaufen (= didaktisch interessant).
2. M2-Skripte (Gemini-Client + Runner + Prompts) zuerst auf den 30 laufen lassen, beide Modi.
3. Akkuranz roh messen, qualitativ analysieren, Prompt iterieren.
4. Erst wenn Prompt v_final sitzt, der Vollauf auf 246.

Außerdem: **Chronologisches Arbeitstagebuch der Iteration** als neue Knowledge-Datei `sample_iteration.md`. Anders als das stabile `data.md` und `requirements.md` ist `sample_iteration.md` chronologisch und wächst mit jeder Prompt-Version.

**Verworfene Alternativen:**

- *Direkt Vollauf mit Prompt v1:* Verworfen, weil 60 Sample-Calls €0.031 kosten und die Iteration realistisch ein bis zwei Runden Verbesserung bringt.
- *Sample-Analyse als Markdown-Dokument:* Verworfen auf Wunsch — wir fixen direkt im Iterations-Loop, ohne separates Analyse-Doc, und halten die Erkenntnisse stattdessen in `sample_iteration.md` fest.
- *Mehrere Modelle parallel testen:* Verworfen, weil Prompt-Tuning ohne Modellwechsel zuerst günstiger und didaktisch lehrreicher ist.

**Konsequenz:**

- Iteration 1 (Prompt v1.0) ist abgeschlossen: Blind 43 % Top-Match, 13 % Leaf-Match. Enriched 53 % Top-Match, 27 % Leaf-Match. Details siehe `sample_iteration.md`.
- Drei systematische Muster identifiziert: (1) Top-Bereich-Magneten (blind→Handwerk, enriched→Hauswirtschaft), (2) Religion vs. Bildwerke konstant verwechselt, (3) sammlungsspezifische Konventionen wie Totschläger→Fischerei sind aus dem Bild allein nicht ableitbar.
- Die Sample-Phase produziert `data/json/sample.json`, `ai_blind_sample.json`, `ai_enriched_sample.json` — alle gitignored, Wegwerf nach M2.
- Der Vollauf wird erst gestartet, wenn der iterierte Prompt eine messbare Verbesserung zeigt.

---

### 2026-04-11 — `.env`-Loader im Repo

**Anlass:** API-Key-Handling. Ursprünglich war `export GEMINI_API_KEY=...` in jeder Shell vorgesehen. Bei mehreren Sessions, Hintergrund-Jobs und IDE-Terminals wird das fehleranfällig — und verleitet dazu, den Key irgendwo abzulegen.

**Entscheidung:** Eine `.env`-Datei im Repo-Root mit `KEY=value`-Zeilen, geladen von `scripts/_common.py` beim Import via `load_env_file()` (eigener Mini-Loader, keine `python-dotenv`-Dependency). `.env` ist in `.gitignore` (verifiziert: `git check-ignore -v .env` zeigt Zeile 28). Bereits gesetzte Umgebungsvariablen gewinnen über die Datei (Shell-Override jederzeit möglich).

**Konsequenz:**

- Jedes Skript, das `_common` importiert, hat `GEMINI_API_KEY` automatisch verfügbar.
- Eine Datei zum Ablegen, eine zum Ignorieren, kein Code-Bezug zum Wert.
