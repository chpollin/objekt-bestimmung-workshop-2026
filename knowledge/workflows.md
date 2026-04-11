# Drei Workflows

Das Projekt zeigt drei aufeinander aufbauende KI-Workflows. Jeder beantwortet eine eigene Frage und liefert eigene Workshop-Erkenntnisse. Im Detail-Drawer der Browser-UI werden alle drei nebeneinander dargestellt — der menschliche Experte sieht, wie sie sich unterscheiden, und entscheidet, welcher gewinnt.

## Übersicht

| Workflow | Was sieht die KI? | Was tut sie? | Workshop-Frage |
|---|---|---|---|
| **A. Blind** | nur das Foto | klassifiziert + beschreibt | Was kann KI ohne jedes Vorwissen aus einem Sammlungsfoto ableiten? |
| **B. Enriched** | Foto + Original-Metadaten | klassifiziert + reichert an | Wie verändert sich das Ergebnis, wenn die KI bestehende Sammlungsdaten als Kontext hat? |
| **C. Judge** | Foto + Original + Antworten von A und B | bewertet, kritisiert, schlägt Korrekturen vor | Kann eine stärkere KI eine schwächere KI sinnvoll bewerten — und finden, was Menschen übersehen? |

C ist **keine** dritte Klassifikation, sondern eine **Meta-Schicht** über A und B. C läuft mit einem stärkeren Modell (`gemini-3-pro-preview`) gegen die Outputs des schwächeren Modells (`gemini-3.1-flash-lite-preview`).

## Workflow A: Blind

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

## Workflow B: Enriched

**Eingabe.** Bild **plus** vorhandene Original-Metadaten: `object_name`, `medium`, `dimensions`, `dated`. Diese kommen aus dem Sammlungsmanagementsystem (Excel-Quelle).

**Ausgabe.** Wie A, aber:
- Beschreibung verwebt Foto und Metadaten zu einem fließenden Katalogtext
- `confidence_note` benennt explizit, **wo Foto und Metadaten widersprechen** — das ist didaktisch zentral

**Pipeline-Schritt.** `python scripts/06_run_gemini.py --mode enriched`

**Was es im Workshop zeigt.** Metadaten verschieben die KI-Entscheidung — nicht immer zum Besseren. Beim Marmoraufsatz im Sample-Run wechselte die KI **mit** Metadaten von „Architektur" (richtig) auf „Wohnen" (falsch), weil das Wort „Marmor" Möbel-Assoziationen triggert. Das ist die Lehre: **mehr Kontext ist nicht automatisch mehr Akkuranz**.

**Wofür es taugt.** Anreicherung bestehender Sammlungen mit konsistenten Beschreibungstexten. Konflikt-Erkennung zwischen Bild und Metadaten („Foto zeigt Metall, Metadaten sagen Holz" — sehr nützlich für Datenqualitätsprüfung).

**Wofür es nicht taugt.** Wenn die Originaldaten fehlerhaft oder verführerisch sind, zieht der Kontext die KI in die Irre.

## Workflow C: Judge

**Eingabe.** Bild + Original-Metadaten + Original-Beschreibung + die JSON-Antworten von Workflow A und B.

**Ausgabe.** JSON mit:
- `verdict`: welcher Workflow gewinnt? (blind / enriched / beide / keiner)
- `judge_top_id`: was hätte der Judge selbst gewählt
- `description_quality_blind`, `description_quality_enriched`: 1–5-Skala
- `prompt_improvement_hints`: konkrete Hinweise, was am Prompt von A oder B unzureichend ist
- `is_collection_quirk`: bool — ist das Original eine sammlungsspezifische Konvention, die aus dem Bild allein nicht ableitbar wäre? (sehr wichtig für faire Bewertung)
- Begründungstext

**Pipeline-Schritt.** `python scripts/07_judge_sample.py` (in Iterationsphase) bzw. `07_judge.py` im Vollauf

**Modell.** `gemini-3-pro-preview` (deutlich stärker als das Flash-Lite-Modell der Workflows A und B). Andere Generation = andere Perspektive.

**Was es im Workshop zeigt.**
1. **KI kann KI bewerten.** Eine zweite KI-Meinung gegen die erste — und sie ist nicht nur ein Spiegel, sondern findet echte Schwächen.
2. **Sammlungs-Quirks werden sichtbar.** Wenn der Judge sagt „das Original ist eine sammlungsspezifische Konvention, die aus dem Bild allein nicht ableitbar wäre", lernen die Teilnehmer: Akkuranz-Prozente sagen nicht alles. Manche „Mismatches" sind keine KI-Fehler.
3. **Iteration wird messbar.** Vor Iteration 2 hat der Judge die Hinweise „Top-Bereich-Magneten in blind", „Material-Trigger in enriched", „Religion/Bildwerke-Verwechslung" aufgelistet. Nach Iteration 2 lässt sich messen: tauchen diese Hinweise noch auf? Damit haben wir einen objektiven Iterations-Stopper.

**Wofür es taugt.** Eval ohne menschlichen Aufwand. Prompt-Iteration. Erklärung der Mismatches im Workshop. Demonstration, dass „KI prüft KI" funktional sein kann.

**Wofür es nicht taugt.** Ground Truth zu setzen, wo es keine gibt. Der Judge ist eine Meinung, nicht die Wahrheit. Auch er kann irren — und genau diese Diskussion ist Teil der Workshop-Story.

## Workflow im UI (M3)

Der Detail-Drawer zeigt vier Karten nebeneinander oder in Tabs:

1. **Original** (read-only, grau, Ground-Truth-Marke) — was die Sammlung sagt
2. **KI Blind** (read-only, lila Badge) — Workflow A
3. **KI Enriched** (read-only, blau Badge) — Workflow B
4. **Judge** (read-only, dunkles Badge mit Modellname) — Workflow C, mit Verdict + Hints
5. **Experte** (editierbar) — die fünfte Spalte, in der der Mensch das letzte Wort hat

Im Akkuranz-Dashboard (FR-8) wird zusätzlich die Judge-Verteilung geführt: wie oft hat der Judge welchem Workflow zugestimmt, wie hoch sind die Beschreibungs-Qualitätsnoten, wie viele Objekte sind als Sammlungs-Quirk markiert.

## Wo leben die Prompts

| Datei | Zweck | Aktuelle Version |
|---|---|---|
| [`../scripts/prompts/system_blind.txt`](../scripts/prompts/system_blind.txt) | System-Prompt für Workflow A | v2.0 |
| [`../scripts/prompts/system_enriched.txt`](../scripts/prompts/system_enriched.txt) | System-Prompt für Workflow B | v2.0 |
| [`../scripts/prompts/system_judge.txt`](../scripts/prompts/system_judge.txt) | System-Prompt für Workflow C | v1.0 |
| [`../scripts/prompts/few_shot_examples.json`](../scripts/prompts/few_shot_examples.json) | 5 echte Katalogtexte als Few-Shot, in Workflow A und B eingebunden | — |

Die Prompt-Versionen sind in den Pipeline-Outputs als `prompt_version`-Feld mitgespeichert (FR-10). Damit lassen sich Antworten verschiedener Prompt-Versionen unterscheiden, ohne die JSON-Outputs zu überschreiben.

**Wie iterieren wir die Prompts?** Jede neue Prompt-Version wird in [`sample_iteration.md`](sample_iteration.md) als Eintrag dokumentiert: Was wurde geändert, warum, gegen welche Sample-Beobachtungen, mit welchem messbaren Effekt (Akkuranz vor/nach, Judge-Verdict). Die Prompt-Dateien selbst sind die Quelle der Wahrheit, das Iterations-Tagebuch ist die Geschichte dahinter.

## Schichten-Logik

Die Disambiguation der Leaf-Listen (siehe ADR-11 in `requirements.md`) ist **kein Teil des Prompts**, sondern wird vom `_gemini_client.py` zur Laufzeit in den Stage-2-Aufruf eingewoben. Wenn ein Leaf-Term mehrfach im Thesaurus vorkommt (34 von 415 Leaf-Termen sind so), bekommt das Modell die Mid-Cluster-Geschwister angezeigt:

```
- AUT.AAW.AAH.AAB.AAB: Hilfsgerät  [Sub-Cluster mit: Werkstatteinrichtung, Hobel, Sägen, …]
- AUT.AAW.AAH.AAC.AAB: Hilfsgerät  [Sub-Cluster mit: Werkstatteinrichtung, Bohrwerkzeuge, …]
```

Das ist datengetrieben aus dem Thesaurus selbst, nicht handgepflegt — und wirkt deshalb auf alle 246 Objekte und beide Modi gleichzeitig.
