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

---

### 2026-04-11 — Vollauf mit Prompt v2.0 auf 245 Objekten

**Anlass:** Sample-Iteration 2 (v2.0) zeigte messbare Verbesserung gegenüber v1.0 in beiden Modi (Blind Top +10pp, Enriched Top +7pp, siehe `sample_iteration.md`). Iteration 3 war als Option diskutiert, aber die zu erwartenden Gewinne lagen in Grenzfällen und hätten weitere Sample+Judge-Runs gekostet.

**Entscheidung:** Vollauf in beiden Modi (blind + enriched) mit Prompt v2.0. Der Judge bleibt auf der handverlesenen 8er-Stichprobe (`judge_selection.json`), kein Voll-Judge. Kosten/Nutzen: ein Voll-Judge auf 245 Objekten mit Gemini 3.1 Pro kostet spürbar mehr als Flash-Lite und bringt für die Workshop-Story marginalen Zusatzgewinn — die 8 handverlesenen Quirks sind das didaktisch wichtige Material.

**Verworfene Alternativen:**

- *Iteration 3:* Die offene Frage aus Sample-Iteration 2 („Enriched auf Metadaten-Priorität + Homonym-Warnung + Inner-Merkmal-Regel tunen") wurde geschlossen. Begründung: v2.0 ist für die Workshop-Story gut genug, Iteration-3-Gewinne wären Grenzfälle, Fehlerquellen sind dokumentiert als didaktisches Material.
- *Voll-Judge auf alle 245 Objekte:* Pro-Modell-Credits für vergleichsweise niedrigen Informationsgewinn. Die Handverlesenen decken alle relevanten Muster (Quirks, Ties, Enriched-Gewinne, Blind-Gewinne) bereits ab.
- *Modellwechsel auf Gemini 3 Flash statt Flash-Lite:* Keine empirische Begründung aus der Sample-Phase, kein Test gemacht. Nachgelagert als Option offen, nicht für den Workshop-Lauf.

**Konsequenz:**

- Finale KI-Outputs in `data/json/ai_blind.json` (245 Records) und `data/json/ai_enriched.json` (245 Records).
- Vollauf-Akkuranz: Blind **50 %** Bereich, **25 %** Leaf · Enriched **61 %** Bereich, **35 %** Leaf. Details in `sample_iteration.md` unter *Vollauf auf 245 Objekten*.
- Der Judge liefert ein verschärftes Signal: in der handverlesenen Stichprobe stimmen 8/8 Judge-Top-Wahlen mit dem Original überein, und bei 3/8 Objekten ist die „falsche" KI-Antwort eigentlich ein Sammlungs-Quirk — das relativiert die Flash-Lite-Prozentzahlen substantiell und ist der didaktische Hebel für den Workshop.

---

### 2026-04-11 — Frontend-Architektur: Hash-Router, Vergleichs-Viewer ohne Editor

**Anlass:** Der ursprüngliche Plan (Phase 3) sah einen **Detail-Drawer** mit Slide-over-Panel und darunter ein **Editor-Formular** mit localStorage-Persistenz und Export-Button („edits.json herunterladen, manuell committen") vor. Beim Bauen der Detail-Ansicht wurde klar, dass der Drawer gegenüber einer echten Unterseite mehrere Probleme hatte — und dass der Editor-Scope für eine Vergleichs-Demo Ballast ist, der das eigentliche didaktische Ziel (Original ↔ KI-Ausgaben nebeneinander stellen) verwässert.

**Entscheidung:**

1. **Hash-Router statt Drawer.** Zwei Routen: `#/` zeigt die Gallery, `#/object/:id` zeigt eine eigene Detail-Seite mit Foto, vier Varianten-Karten (Original, KI blind, KI erweitert, Judge wenn vorhanden) und Prev/Next-Navigation. Browser-Back/Forward funktioniert, Direkt-Links auf einzelne Objekte sind möglich, ESC und Pfeiltasten nur in der Detail-Seite.
2. **Kein Editor, kein Export, kein localStorage.** Die App ist ein reiner Read-Only-Vergleichs-Viewer. Der Experte im Workshop-Kontext *vergleicht* und *diskutiert*, er editiert nicht. FR-2 („optionaler Experten-Edit"), FR-4 („Detail-Drawer mit Editor"), FR-6 („Export als edits.json") und FR-7 („edits.json Merge beim Laden") werden in `requirements.md` als gestrichen markiert.
3. **Statuswert-Set auf drei reduziert:** `match` (🟢 Übereinstimmung), `conflict` (🔴 Top-Bereich-Konflikt), `noai` (⚪ keine KI-Daten). Die Zustände „freigegeben" und „ungeprüft" aus FR-5 entfallen mit dem Editor.

**Verworfene Alternativen:**

- *Slide-over-Drawer* wie im Ursprungsplan: Browser-Navigation gebrochen, keine Direkt-Links, fragiler bei Beamer-Zoom, und das Layout mit Foto links / Content rechts macht auf einer eigenen Seite mehr visuell ruhigen Platz.
- *Modal-Dialog:* Fokus-Falle, schließt bei ESC, aber bricht die Back-Taste genauso wie der Drawer.
- *Light-Editor mit nur einem Freitextfeld („Anmerkung"):* Halber Weg, verwirrt die Workshop-Teilnehmenden („darf ich jetzt editieren oder nicht?") und zieht ein Export-Feature nach sich.
- *localStorage-Persistenz ohne Export:* Hätte die Kommentare nur lokal gehalten. Didaktisch wertlos (verschwinden bei Cache-Clear), aber auch hier: verwirrt die Workshop-Geschichte.

**Konsequenz:**

- `index.html` hat zwei `.view`-Container (`#view-gallery`, `#view-detail`), der Router toggled `hidden`.
- `app.js` hat zwölf nummerierte Sektionen von `CONFIG` über `STATE`, `LOADER`, `FILTERS`, `RENDER-gallery`, `RENDER-sidebar`, `RENDER-detail-page`, `DASHBOARD` bis `ROUTER` und `BOOT`. Kein Editor-Code, kein localStorage, kein Export-Button.
- Dashboard-Konfusions-Liste wurde als Folge *klickbar* gemacht (Filter pinnt sich auf das betreffende `fromTop → toTop`-Paar), weil ohne Editor die einzige sinnvolle Interaktion Drill-Down und Vergleich ist.
- Judge-Quirks werden auf der Original-Karte mit einem gelben Banner markiert — das ist die didaktisch wichtigste Ergänzung nach der Scope-Entscheidung, weil sie „die KI ist nicht falsch, die Sammlung hat eine Konvention" direkt im UI zeigt.
- Workshop-Tag-Risiko bleibt bei null: kein Nutzer-Input, der fehlschlagen könnte, keine State-Mutation, keine externen Requests.

---

### 2026-04-11 — Objekt 1168643 aus dem Scope entfernt

**Anlass:** Beim Bild-Download scheiterte die Übertragung für `1168643` drei Mal in Folge (`scripts/download_report.txt`: „failed after 3 retries: dispatcher/336606"). Das Objekt blieb in `objects.json` und `originals.json`, hatte aber weder ein lokales Bild noch KI-Outputs — eine leere Kachel mit Status `noai` in der Galerie, ohne didaktischen Wert.

**Entscheidung:** Objekt `1168643` aus `data/json/objects.json` und `data/json/originals.json` entfernen, Zielzahl der Selektion überall konsistent auf **245**. Alle anderen Daten-JSONs (`ai_blind.json`, `ai_enriched.json`, `ai_judge.json`) sind bereits ohne das Objekt, daher keine weiteren Änderungen nötig.

**Verworfene Alternativen:**

- *Vierter Download-Retry:* Der Fehler wiederholte sich dreimal — nicht transient. Ein weiterer Versuch würde im besten Fall funktionieren, aber einen Nachlauf (Preview-Bild, beide Gemini-Calls, Index-Rebuild) erzwingen, für marginal größere Selektion. Nutzen gering, Arbeit zu viel.
- *Objekt drin lassen als Edge-Case-Beispiel:* Die leere Kachel müsste im Workshop erklärt werden („das eine Objekt hat kein Bild"), lenkt vom eigentlichen Vergleich ab und sieht im Galerie-Grid schlampig aus.

**Konsequenz:**

- Fünf Daten-JSONs konsistent auf 245 Records: `objects.json`, `originals.json`, `ai_blind.json`, `ai_enriched.json` mit jeweils 245, plus `ai_judge.json` mit seinen 8 handverlesenen Einträgen.
- `scripts/download_report.txt` bleibt unverändert als Audit-Spur für die Entscheidung.
- Frontend-Gallery-Header zeigt „245 Objekte".
