# Anforderungen

Single Source of Truth für *Objekt-Bestimmung Workshop 2026*. Diese Datei enthält das **stabile** Projektwissen: Was das System leisten soll, was bewusst ausgeschlossen ist und welche Architekturentscheidungen wir getroffen haben. Sie darf nie hinter dem Code zurückbleiben — wenn sich Anforderungen ändern, wird sie zuerst aktualisiert.

Operative Inhalte (Datenfluss, Komponenten, Verifikation) leben in [`data.md`](data.md). Workshop-Story und die drei Workflows in [`workflows.md`](workflows.md). Chronologie in [`journal.md`](journal.md), aktuelle Iterationen in [`sample_iteration.md`](sample_iteration.md).

## 1. Projektziel

Demo & Lehrmaterial für den Workshop „Kann KI kulturgeschichtliche Objekte bestimmen — und was brauchte es dafür?" am 20.04.2026 in Salzburg. Zeigt Museumsfachleuten, wie ein Vision-LLM aus Sammlungsfotos sammlungskonforme Beschreibungen und Thesaurusbegriffe ableitet, ohne Training oder Fine-Tuning. Ist gleichzeitig ein Vergleichs-Viewer, mit dem KI-Vorschläge gegen Originaldaten und Judge-Urteile nebeneinander gestellt werden können — kein Editor.

## 2. Zielgruppe und Erfolgskriterien

**Zielgruppe:** Museumsfachleute ohne ML-Kenntnisse.

**Erfolgskriterien:**

- Workshop-Teilnehmende verstehen am Ende, was KI bei Sammlungsobjekten leistet und wo sie scheitert.
- Das Tool funktioniert offline und auf GitHub Pages.
- Original und KI-Varianten lassen sich pro Objekt bequem nebeneinander vergleichen.
- Die Demo läuft am Workshop-Tag deterministisch (kein Live-API-Risiko).

## 3. Funktionale Anforderungen (FR)

| ID    | Anforderung |
|-------|-------------|
| FR-1  | Das System stellt 245 kuratierte Objekte aus der volkskundlichen Sammlung der Landessammlungen NÖ als durchsuchbare Galerie dar. |
| FR-2  | Jedes Objekt zeigt: Foto, Originalmetadaten, KI-Beschreibung im Modus „blind", KI-Beschreibung im Modus „erweitert", Judge-Urteil (bei handverlesener 8er-Stichprobe). |
| FR-3  | Filter: Thesaurus-Hierarchie (collapsible Tree), Freitextsuche (Objektname/Term/Material/Maße/Datierung/Katalogtext), Status (Übereinstimmung/Konflikt/keine KI). Datierung als eigene Filterdimension gestrichen — nicht Kern der Vergleichs-Story. |
| FR-4  | Detail-Seite (eigene Route `#/object/:id`) zeigt alle vier Varianten nebeneinander: Original, KI blind, KI erweitert, Judge (wenn vorhanden). Keine Editier-Funktion. Prev/Next-Navigation zwischen gefilterten Nachbarobjekten. |
| FR-5  | Statusanzeige pro Objekt (drei Werte): 🟢 Übereinstimmung (KI-blind Top-Bereich = Original), 🔴 Konflikt, ⚪ keine KI-Daten. |
| FR-6  | *(gestrichen)* Export-Funktion entfällt — siehe ADR-14. |
| FR-7  | *(gestrichen)* `edits.json` entfällt — siehe ADR-14. |
| FR-8  | Übersichtsstatistik („Akkuranz-Dashboard"): drei Panels — Akkuranz (Bereich/Leaf, beide Modi), häufigste Verwechslungen (klickbar, pinnt Filter auf `fromTop → toTop`-Paar), Judge-Panel (Quirk-Anteil als Hero-Metric plus Quality-Mittel). |
| FR-9  | Pipeline ist resume-fähig und reproduzierbar (alle Outputs deterministisch außer Modell-Antworten). |
| FR-10 | Pipeline-Output-JSONs enthalten ein `prompt_version`-Feld, damit verschiedene Prompt-Iterationen unterscheidbar sind. |
| FR-11 | LLM-as-a-Judge bewertet eine handverlesene Stichprobe von 8 Objekten gegen Original und Bild und schlägt Verbesserungen vor. Ergebnis ist eine vierte Variante auf der Detail-Seite. Quirks werden zusätzlich als Banner auf der Original-Karte hervorgehoben. |

## 4. Nicht-funktionale Anforderungen (NFR)

| ID    | Anforderung |
|-------|-------------|
| NFR-1 | Statische Site, kein Build-Step, kein Bundler, keine Frameworks (Vanilla HTML/CSS/JS). |
| NFR-2 | Auf GitHub Pages deploybar ohne Konfiguration. |
| NFR-3 | Funktioniert vollständig offline (kein Live-API-Call zur Laufzeit, kein CDN). |
| NFR-4 | Repo-Größe < 100 MB (Bilder resized, kein Git LFS notwendig). |
| NFR-5 | Beamer-tauglich: hoher Kontrast, Schriftgrößen ≥ 16px, klare Statusfarben. |
| NFR-6 | UI-Sprache Deutsch, Code-Kommentare und Commit-Messages Englisch. |
| NFR-7 | Code lesbar und kommentiert für Workshop-Teilnehmende, die ihn nachvollziehen wollen. |
| NFR-8 | Keine externen Abhängigkeiten zur Laufzeit (kein CDN, keine Webfonts). |
| NFR-9 | Daten und Bilder unterliegen Urheberrecht der Landessammlungen NÖ — Hinweis im README, keine Weiterverbreitung. |

## 5. Architekturentscheidungen (ADR)

| ID    | Entscheidung | Begründung | Verworfene Alternativen |
|-------|--------------|------------|-------------------------|
| ADR-1 | Vorberechnete Pipeline statt Live-Browser-API-Calls | CORS blockiert Bild-Fetch im Browser. Workshop-Tag-Risiko vermieden. Reproduzierbar. | Live-API mit User-Key (CORS-Problem); Public CORS-Proxy (fragil) |
| ADR-2 | Zweistufiger Gemini-Call (Top-Bereich → Leaf-Term) | Geminis Enum-Limit ~120, größter Top-Bereich hat 98 Leafs → harte Constraints in beiden Stufen möglich, keine Halluzination | Single-Call mit Post-Validierung (Restrisiko), Single-Call ohne Constraint (didaktisch ehrlich aber praktisch unbrauchbar) |
| ADR-3 | Beide Modi parallel (blind + enriched) | Didaktisch entscheidend: zeigt Erkennungs-Use-Case und Anreicherungs-Use-Case nebeneinander | Nur einer von beiden — verfehlt entweder Erkennungs- oder Anreicherungsfrage |
| ADR-4 | Lokale Bilder im Repo statt Hotlinking | CORS, Performance, Offline-Fähigkeit, Workshop-Tag-Stabilität | Hotlinking, CORS-Proxy, Git LFS (nicht nötig bei resized JPGs) |
| ADR-5 | *(ersetzt durch ADR-14)* Ursprünglich: localStorage + Export-Datei statt Backend. Mit der Streichung des Editor-Scopes in ADR-14 ist diese Entscheidung obsolet — die Site ist ein reiner Vergleichs-Viewer ohne persistenten Zustand. | — | — |
| ADR-6 | Hierarchischer Thesaurus mit aus Onlinesammlung ergänzten Top-Bereich-Namen | Excel hat nur Leaf-Namen, nicht Eltern. Onlinesammlung listet 21 Volkskunde-Bereiche auf. | Platzhalter „CN-Suffix" (Pfusch), manuelle Liste (mehr Aufwand, gleiche Quelle) |
| ADR-7 | Few-Shot-Prompts mit echten Katalogtexten der Onlinesammlung | Excel hat keine Beschreibungstexte. Onlinesammlungs-Detailseiten haben sie im richtigen Stil. | Stilbeschreibung in Worten (schwächeres Signal), keine Few-Shots (KI driftet) |
| ADR-8 | 245 Objekte stratifiziert nach Top-Bereich, max. 3 pro Leaf | Maximale Vielfalt bei begrenzter Pipeline-Dauer und Repo-Größe (Ziel war ~250, final 245 nach Entfernen von 1168643) | 10–15 (zu wenig für Showcase), 50 pro Top (zu groß), alle 10.722 (unmöglich) |
| ADR-9 | Knowledge-Basis im Repo unter `knowledge/` | Anforderungen müssen mitwachsen und für andere lesbar sein | Plan-Datei in `~/.claude/plans/` (nur lokal sichtbar, vergänglich) |
| ADR-10 | Ordnerstruktur: `scripts/` (statt `pipeline/`) und `data/json/` für JSON-Outputs | Existierende Repo-Struktur respektieren statt parallele Hierarchie aufbauen | `pipeline/` + `data/*.json` (würde leere Verzeichnisse hinterlassen) |
| ADR-11 | Stage-2-Disambiguation: Geschwister-Namen im Prompt anzeigen | 34 Leaf-Term-Namen kommen mehrfach vor (z.B. „Hilfsgerät" 10×). Ohne Mid-Cluster-Hint kann das Modell sie nicht trennen. Empirisch in Sample-Iteration 1 bestätigt. | Stumpfe Leaf-Liste (Iteration 1, schwache Akkuranz), Mid-Level-Namen aus Web scrapen (Endpoint existiert nicht) |
| ADR-12 | LLM-as-a-Judge als dritte Schicht | Manuelle Bewertung skaliert nicht. Stärkeres Modell (Gemini 3 Pro) als Judge gegen schwächeres Modell (Flash Lite) liefert objektive Iterationsmetrik UND Workshop-Material („Kann KI eine KI bewerten?"). | Nur menschliche Bewertung (zu langsam), gleiches Modell als Judge (kein Mehrwert) |
| ADR-13 | Daten via JSON-Endpoint `/objects/{id}/json`, nicht via HTML-Scraping | Endpoint liefert sauberes Label/Value-Schema mit allen benötigten Feldern. | BeautifulSoup-Scraping (fragiler, kein Vorteil) |
| ADR-14 | Vergleichs-Viewer statt Editor | Workshop-Story ist *Original ↔ KI-Ausgaben vergleichen*, nicht *Reviewen und Freigeben*. Jede Edit-Interaktion würde den Workshop-Flow unterbrechen, erhöht das Risiko am Workshop-Tag und verwässert die didaktische Kernfrage. Read-Only → null persistenter Zustand, null Failure-Modes. | Editor-Form mit localStorage-Export (Ursprungsplan, FR-2/4/6/7), „light editor" mit nur einem Freitext-Feld (halber Weg, verwirrend), Annotation-Feature ohne Persistenz (sinnlos). Siehe Journal 2026-04-11 *Frontend-Architektur*. |
| ADR-15 | Hash-Router mit echter Detail-Seite statt Slide-over-Drawer | Browser-Back/Forward funktioniert, Direkt-Links auf `#/object/:id` sind möglich, beamertauglicher Layout ohne Overlay-Artefakte, Fokus auf ein Objekt. Der Router braucht nur wenige Zeilen, keine Library. | Slide-over-Drawer (Browser-Navigation gebrochen, fragile bei Zoom), Modal-Dialog (Fokus-Falle, bricht Back-Taste), Tabs innerhalb der Gallery (kein Direkt-Link). Siehe Journal 2026-04-11 *Frontend-Architektur*. |

## 6. Out of Scope (explizit)

- Live-API-Calls aus dem Browser
- API-Key-Eingabe-Feld im Frontend
- Backend, Datenbank, User-Authentifizierung
- Editor- und Export-Funktion: Im Laufe der Umsetzung zugunsten eines reinen Vergleichs-Viewers gestrichen (siehe ADR-14, Journal 2026-04-11 *Frontend-Architektur*). Betroffen: FR-2 (Editor), FR-4 (Drawer+Editor), FR-6 (Export), FR-7 (`edits.json`-Merge), FR-5 („freigegeben/ungeprüft"-Status).
- Vollständige 10.722 Objekte im Tool
- Mehrsprachigkeit der UI
- Test-Suite oder CI (manuelles Testen via Verifikation in `data.md`)
- Tastatur-Shortcuts in der Gallery. Einzige Ausnahme: ESC und Pfeiltasten in der Detail-Seite für essenzielle Navigation.
- Iteration 3 der Prompts (entschieden am 2026-04-11, siehe Journal *Vollauf*)
- Voll-Judge auf alle 245 Objekte (nur handverlesene 8er-Stichprobe, siehe FR-11)

## 7. Annahmen und Risiken

| Risiko / Annahme | Stand | Mitigation |
|------------------|-------|------------|
| Gemini-API-Kosten | Vollauf abgeschlossen. | Erledigt |
| Onlinesammlung könnte Scraping blockieren | Bisher keine Blockade. JSON-Endpoint liefert 4/250 mal 403, vermutlich permanent. | Höflich: User-Agent, 1s Sleep, Caching pro Objekt-ID, automatisches Filtern unerreichbarer Objekte. |
| Pillow-Resize-Auflösung | 1024 px gewählt; nicht empirisch validiert. | A/B-Test wurde nicht durchgeführt — im Vollauf keine auffällige Auflösungs-bedingte Degradation, daher akzeptiert. |
| Bilder-Repo-Größe | Nach Vollauf: 17 MB für 245 Bilder, Repo insgesamt 38 MB. Sicher unter NFR-4. | Erledigt |
| Objekt 1168643 ohne Bild | Bild-Download schlug 3× fehl. | Erledigt durch Entfernen aus `objects.json` + `originals.json`, siehe Journal *Objekt 1168643 aus dem Scope entfernt*. |
| Workshop-Tag Beamer-Lesbarkeit | Nicht am Beamer im Zielraum verifiziert. | Dry-Run am 19.04.2026 (Paket 7 des Abschlussplans). Quick-Fix-Option: `--text: #333333` → `#000000` in `style.css`. |
