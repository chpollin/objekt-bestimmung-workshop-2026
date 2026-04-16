# Drei Workflows

Das Projekt zeigt drei aufeinander aufbauende KI-Workflows. Jeder beantwortet eine eigene Frage und liefert eigene Workshop-Erkenntnisse. Auf der Detail-Seite der Browser-UI (`#/object/:id`) werden alle drei nebeneinander dargestellt, sodass Original und KI-Varianten direkt vergleichbar sind.

## Übersicht

| Workflow | Was sieht die KI? | Was tut sie? | Workshop-Frage |
|---|---|---|---|
| **A. Blind** | nur das Foto | klassifiziert + beschreibt | Was kann KI ohne jedes Vorwissen aus einem Sammlungsfoto ableiten? |
| **B. Enriched** | Foto + Original-Metadaten | klassifiziert + reichert an | Wie verändert sich das Ergebnis, wenn die KI bestehende Sammlungsdaten als Kontext hat? |
| **C. Korrektur** | Foto + Metadaten + Enriched-Antwort | prüft, korrigiert, liefert finale Fassung | Kann ein stärkeres Modell die Arbeit eines kleineren abschließen und in eine sammlungsreife Fassung überführen? |

C ist die **finale Fassung**, nicht nur Bewertung. Ein stärkeres Modell (`gemini-3.1-pro-preview`) liest die Arbeit des schwächeren Modells (`gemini-3.1-flash-lite-preview`) und erzeugt die Klassifikation plus Katalogeintrag, die in die Sammlung wandern könnten. Details in ADR-12 und FR-11 in `requirements.md`.

## Workflow A: Vision-LLM, nur Foto

**Eingabe.** Bild als JPEG, max. 1024 px lange Kante. Keine weiteren Informationen.

**Ausgabe.** JSON mit:
- gewähltem Top-Bereich (1 von 20)
- gewähltem Leaf-Term (1 von ~80–100, abhängig vom Top-Bereich)
- 1–3-Sätze-Beschreibung im Sammlungsstil
- Material/Technik (wenn sichtbar)
- Datierung (wenn stilistisch ableitbar)
- `confidence_note`: explizite Benennung der eigenen Unsicherheit
- `stage1_reasoning`: Begründung der Top-Bereich-Wahl

**Pipeline-Schritt.** `python scripts/06_run_gemini.py --mode blind`

**Was es im Workshop zeigt.** Die KI entscheidet auf Basis von **Form und sichtbarem Material**, nicht auf Basis von Sammlungslogik. Eine Hacke ist physisch ein Werkzeug → die KI schlägt zunächst Handwerk vor. Die Sammlung ordnet aber nach **Lebenskontext**: dieselbe Hacke kann in der Forstwirtschaft, im Gartenbau oder in einem Brauchtum sein. Der Mismatch ist die Lehre.

**Wofür es taugt.** Erstkontakt mit unbekannten Beständen. Schnelle Vorklassifikation. Erkennen, was ein Objekt **physikalisch** ist.

**Wofür es nicht taugt.** Sammlungsspezifische Konventionen, Provenienz, Datierung jenseits stilistischer Marker, kontextuelle Klassifikationen.

## Workflow B: Vision-LLM, Foto + Metadaten

**Eingabe.** Bild **plus** vorhandene Original-Metadaten: `object_name`, `medium`, `dimensions`, `dated`. Diese kommen aus dem Sammlungsmanagementsystem (Excel-Quelle).

**Ausgabe.** Wie A, aber:
- Beschreibung verwebt Foto und Metadaten zu einem fließenden Katalogtext
- `confidence_note` benennt explizit, **wo Foto und Metadaten widersprechen** — das ist didaktisch zentral

**Pipeline-Schritt.** `python scripts/06_run_gemini.py --mode enriched`

**Was es im Workshop zeigt.** Metadaten verschieben die KI-Entscheidung — nicht immer zum Besseren. Beim Marmoraufsatz im Sample-Run wechselte die KI **mit** Metadaten von „Architektur" (richtig) auf „Wohnen" (falsch), weil das Wort „Marmor" Möbel-Assoziationen triggert. Das ist die Lehre: **mehr Kontext ist nicht automatisch mehr Akkuranz**.

**Wofür es taugt.** Anreicherung bestehender Sammlungen mit konsistenten Beschreibungstexten. Konflikt-Erkennung zwischen Bild und Metadaten („Foto zeigt Metall, Metadaten sagen Holz" — sehr nützlich für Datenqualitätsprüfung).

**Wofür es nicht taugt.** Wenn die Originaldaten fehlerhaft oder verführerisch sind, zieht der Kontext die KI in die Irre.

## Workflow C: Korrektur (finale Fassung)

**Eingabe.** Bild + Original-Metadaten (Objektname, Material, Maße, Datierung) + die JSON-Antwort von Workflow B (Enriched). Den Original-Eintrag der Sammlung bekommt der Korrektor **nicht** — er arbeitet realistisch für den Produktionsfall (neue Objekte haben keinen Original-Eintrag). Die Original-Zuordnung wird nur nachträglich für die Evaluation verwendet.

**Ausgabe.** JSON mit:
- `final_top_id`: finaler Top-Bereich (enum-beschränkt auf die 20 Lebensbereiche)
- `final_thesaurus_id`: finale Unterkategorie (enum-beschränkt auf Leaves des gewählten Top-Bereichs)
- `final_description`: sammlungsreifer Katalogeintrag, 2–4 Sätze
- `final_confidence_note`: offene Punkte, ggf. plausible Alternativen
- `corrections_applied`: Liste mit Kurzbegründung pro Änderung gegenüber der Enriched-Fassung (leer, wenn nur Stilschliff)
- `curator_review_needed`: bool — true, wenn die Zuordnung aus Foto und Metadaten allein nicht eindeutig ableitbar ist (Sammlungs-Eigenheit, Homonym-Falle)
- `stage1_reasoning`: Begründung der Top-Bereich-Wahl

**Pipeline-Schritt.** `python scripts/07_correct_sample.py`

**Modell.** `gemini-3.1-pro-preview` (deutlich stärker als das Flash-Lite-Modell der Workflows A und B). Zweistufig wie A und B: erst Top-Bereich, dann Leaf + Beschreibung.

**Was es im Workshop zeigt.**
1. **Kleine Modelle plus großes Modell funktioniert.** Das billige Modell leistet die Grundarbeit, das teure korrigiert — realistisches Muster für Produktionsworkflows.
2. **Korrekturen sind begründet.** `corrections_applied` macht nachvollziehbar, was geändert wurde und warum. Kein Black-Box-Ergebnis, sondern Auditspur.
3. **Grenzen werden sichtbar.** Wenn der Korrektor `curator_review_needed = true` setzt, erkennt er selbst, dass eine Zuordnung aus Evidenz allein nicht erschließbar ist. Der Mensch übernimmt gezielt dort, wo die KI auf ihre Grenzen stößt.

**Wofür es taugt.** Anreicherung neuer Objekte ohne bestehenden Katalogeintrag. Qualitätsprüfung mit nachvollziehbarer Korrektur-Spur. Filterung der Fälle, die einer Kuratorin vorgelegt werden sollen.

**Wofür es nicht taugt.** Sammlungskonventionen, die nur in der kuratorischen Dokumentation leben (Homonyme mit Fachzuordnung, Funktionsverortung). Solche Fälle markiert der Korrektor korrekt als prüfungsbedürftig, kann sie aber nicht eigenständig auflösen.

## Workflow im UI

Die Detail-Seite (`#/object/:id`) zeigt vier Karten read-only untereinander in der rechten Spalte, links daneben das große Foto:

1. **Original** (Ground-Truth, grau) — was die Sammlung sagt. Trägt bei Objekten mit `curator_review_needed = true` zusätzlich einen gelben Banner *„Korrektor: Zuordnung aus Evidenzmaterial nicht eindeutig — Sammlungs-Eigenheit, kuratorische Prüfung empfohlen"*.
2. **KI Blind** (lila Badge) — Workflow A.
3. **KI Enriched** (blau Badge) — Workflow B.
4. **Korrektur / Finale Fassung** (dunkles Badge mit Modellname) — Workflow C, mit finalen Klassifikations- und Beschreibungsfeldern, Liste der angewandten Korrekturen und Konfidenz-Notiz.

Es gibt keine Experten-Edit-Spalte — die Site ist ein reiner Vergleichs-Viewer (siehe ADR-14). Änderungen an der Klassifikation passieren außerhalb des Tools, im Sammlungsmanagementsystem.

Im Akkuranz-Dashboard (FR-8) wird zusätzlich die Korrektor-Auswertung geführt: Top-Match-Quote der finalen Fassung, Anzahl der Bereichs-Änderungen gegenüber Enriched (mit Treffer-Effekt), Anzahl der Objekte mit angewandten Korrekturen, Anzahl der für kuratorische Prüfung geflaggten Objekte. Die „häufigste Verwechslungen"-Liste ist klickbar — ein Klick pinnt einen Filter auf das betreffende `fromTop → toTop`-Paar, sodass man direkt in die Betroffenen-Objekte springt.

## Wo leben die Prompts

| Datei | Zweck | Aktuelle Version |
|---|---|---|
| [`../scripts/prompts/system_blind.txt`](../scripts/prompts/system_blind.txt) | System-Prompt für Workflow A | v3.0 |
| [`../scripts/prompts/system_enriched.txt`](../scripts/prompts/system_enriched.txt) | System-Prompt für Workflow B | v3.0 |
| [`../scripts/prompts/system_corrector.txt`](../scripts/prompts/system_corrector.txt) | System-Prompt für Workflow C | v1.0 |
| [`../scripts/prompts/few_shot_examples.json`](../scripts/prompts/few_shot_examples.json) | 5 echte Katalogtexte als Few-Shot, in Workflow A und B eingebunden | — |

Die Prompt-Versionen sind in den Pipeline-Outputs als `prompt_version`-Feld mitgespeichert (FR-10). Damit lassen sich Antworten verschiedener Prompt-Versionen unterscheiden, ohne die JSON-Outputs zu überschreiben.

**Wie iterieren wir die Prompts?** Jede neue Prompt-Version wird in [`sample_iteration.md`](sample_iteration.md) als Eintrag dokumentiert: Was wurde geändert, warum, gegen welche Sample-Beobachtungen, mit welchem messbaren Effekt (Akkuranz vor/nach). Die Prompt-Dateien selbst sind die Quelle der Wahrheit, das Iterations-Tagebuch ist die Geschichte dahinter.

## Schichten-Logik

Die Disambiguation der Leaf-Listen (siehe ADR-11 in `requirements.md`) ist **kein Teil des Prompts**, sondern wird vom `_gemini_client.py` zur Laufzeit in den Stage-2-Aufruf eingewoben. Wenn ein Leaf-Term mehrfach im Thesaurus vorkommt (34 von 415 Leaf-Termen sind so), bekommt das Modell die Mid-Cluster-Geschwister angezeigt:

```
- AUT.AAW.AAH.AAB.AAB: Hilfsgerät  [Sub-Cluster mit: Werkstatteinrichtung, Hobel, Sägen, …]
- AUT.AAW.AAH.AAC.AAB: Hilfsgerät  [Sub-Cluster mit: Werkstatteinrichtung, Bohrwerkzeuge, …]
```

Das ist datengetrieben aus dem Thesaurus selbst, nicht handgepflegt — und wirkt deshalb auf alle 245 Objekte und beide Modi gleichzeitig.
