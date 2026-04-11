# Sample-Iteration

Arbeitstagebuch der Sample-/Prompt-Iterationsphase. Anders als `data.md` (stabile Bestandsaufnahme) und `requirements.md` (Single Source of Truth) ist diese Datei **chronologisch** und wird mit jedem Prompt-Lauf erweitert.

Zweck: Dokumentieren, wie wir vom ersten naiven Prompt zur finalen Version gekommen sind, welche Fälle Erkenntnisse gebracht haben und welche Hypothesen wir verworfen haben. Wichtig für späteres Auditing und für den Workshop, weil die Iterationsstory selbst Teil der Lehrgeschichte ist.

Aktuelles Sample: 30 Objekte aus `data/json/sample.json`, deterministisch gewählt von `scripts/sample_select.py` (gitignored, Wegwerf nach M2).

---

## Iteration 1 — Prompt v1.0

**Datum:** 2026-04-11
**Modell:** `gemini-3.1-flash-lite-preview`
**Prompts:** `scripts/prompts/system_blind.txt` v1.0 / `scripts/prompts/system_enriched.txt` v1.0
**Few-Shots:** 5 Stück, gewählt von `03_scrape_originals.py`, gespeichert in `scripts/prompts/few_shot_examples.json`
**Kosten:** €0.031 für 60 Calls (30 blind + 30 enriched)
**Latenz:** ~4–6 Sekunden pro Call

### Akkuranz auf 30 Sample-Objekten

|             | Top-Match | Leaf-Match |
|-------------|-----------|------------|
| Blind       | 13/30 (43 %) | 4/30 (13 %) |
| Enriched    | 16/30 (53 %) | 8/30 (27 %) |

Übereinstimmung der beiden Modi untereinander: 19/30 gleiche Top-Wahl, 13/30 gleiche Leaf-Wahl. Heißt: enriched bringt eine **andere** Klassifikation, nicht nur eine bessere — die zusätzlichen Metadaten verschieben die Entscheidung.

### Beobachtungen

**1. Top-Bereich-Magneten verzerren das Bild.**
- Blind zieht Werkzeug-ähnliche Objekte (Hacke, Peitsche, Schachtel, Totschläger) reflexartig nach `Handwerk/Industrie/Handel`. Die Sammlung trennt aber nach Kontext: Hacke→Forstwirtschaft, Peitsche→Brauch und Fest, Totschläger→Fischerei (das war eine Überraschung — siehe unten), Schachtel→Gesundheit.
- Enriched zieht Objekte mit Material-Stichworten reflexartig nach `Hauswirtschaft`. Beispiele: Marmoraufsatz, Trog, Schachtel.

**2. Religiöses vs. Bildwerke ist konstant verwechselt.**
- `Heiligenfigur` (Devotionalien) → KI sagt Bildwerke (`AUT.AAW.AAS`)
- `Bild` (Religiöse Darstellungen) → KI sagt Religion (`AUT.AAW.AAP`)
- Die Modell-Logik ist invertiert zur Sammlungslogik. Beide Modi machen denselben Tausch.

**3. Originalklassifikation überrascht selbst Menschen.**
- `Totschläger` ist im Original unter `Volkskunde – Fischerei` (Zubehör), nicht Strafvollzug oder Jagd. Vermutlich eine sammlungsspezifische Konvention.
- `Habergeiß` (Brauchtum) wird blind als Landwirtschaft (Tier) eingestuft — naheliegend ohne Kontext, aber falsch.
- Diese Fälle sind didaktisch wertvoll: sie zeigen, dass Sammlungslogik nicht aus dem Bild ableitbar ist.

**4. Stage-1-Reasoning ist meistens kurz und plausibel.**
- Beispiel Marmoraufsatz blind: „Das Objekt ist ein architektonisches Bauelement, vermutlich ein Kapitell oder eine Basis." → Top-Wahl korrekt.

**5. confidence_note erfüllt ihren Zweck.**
- Beispiel Marmoraufsatz: „Es ist unklar, ob es sich um ein architektonisches Element wie einen Türknauf, einen Teil eines Türbeschlags oder ein anderes Bauteil handelt." Das Modell bekennt seine Mehrdeutigkeit ehrlich.

**6. Beschreibungsstil sitzt schon in v1.**
- Lakonisch, präzise, deutsch. Keine Marketing-Sprache. Few-Shots wirken.

**7. Halluzinationen: bisher keine entdeckt.**
- Keine erfundenen Inschriften, keine Wunsch-Datierung. Auch enriched kopiert nicht stumpf die Metadaten.

### Offene Fragen für Iteration 2

- **Sollen wir Top-Bereich-Magneten gegensteuern?** Z.B. im Prompt explizit warnen: „Werkzeuge stehen nicht automatisch in Handwerk/Industrie/Handel. Frage dich: in welchem realen Lebenskontext wurde dieses Objekt benutzt?"
- **Sollen wir Sammlungslogik-Hinweise einbauen?** Z.B. „Religiöse Bildwerke sind in `Religion und Glaube` (Devotionalien), nicht in `Bildwerke`. `Bildwerke` enthält weltliche Druckgrafik und Modellierungen."
- **Lohnt es sich, dem Modell Beispiele für besonders verwirrende Konventionen zu geben?**
- **Brauchen wir weitere Few-Shots aus den Top-Bereichen, die im aktuellen Sample untervertreten sind?** (Few-Shots sind alle aus 5 Bereichen — bei 20 Top-Bereichen bleibt das eine schmale Basis.)
- **Hilft eine höhere Bildauflösung?** Aktuell 1024 px. A/B-Test 768/1024/1536 ist im Plan.

### Nicht angefasst, aber im Hinterkopf

- Modell-Wechsel auf `gemini-3-flash-preview` (stärker, teurer). Erst wenn Prompt-Iteration ausgereizt ist.
- Längeres `confidence_note` als Soft-Zwang. Aktuell schreibt das Modell oft nur einen Satz; mehr wäre für den Workshop oft besser.

### Status

- Iteration 1 **abgeschlossen**.

---

## Iteration 2 — Prompt v2.0

**Datum:** 2026-04-11
**Prompts:** `system_blind.txt` v2.0, `system_enriched.txt` v2.0
**Architektur-Änderung:** Stage-2 Leaf-Liste bekommt für duplizierte Term-Namen Mid-Cluster-Geschwister als Disambiguator (34 von 415 Leafs sind Duplikate, „Hilfsgerät" 10×). Implementiert in `_gemini_client.py`. Siehe ADR-11.
**Few-Shots:** unverändert
**Kosten:** €0.037 für 60 Calls (30 blind + 30 enriched)

### Inhaltliche Änderungen gegenüber v1

**Beide Prompts:** expliziter Lebenskontext-Hinweis mit konkreten Beispielen (Hacke im Wald vs. Feld vs. Schmiede, Trog für Fütterung vs. Lebensmittel, Spardose→Öffentlichkeit).

**Beide Prompts:** klare Religion-vs-Bildwerke-Regel: religiöse Objekte immer in Religion und Glaube, Bildwerke sind weltliche Darstellungen.

**Enriched:** zusätzliche Warnung vor Material-Triggern („Marmor nicht automatisch Wohnen").

### Akkuranz auf 30 Sample-Objekten

|             | Top-Match v1 | Top-Match v2 | Leaf-Match v1 | Leaf-Match v2 |
|-------------|--------------|--------------|---------------|---------------|
| Blind       | 13/30 (43 %) | **16/30 (53 %)** | 4/30 (13 %) | **8/30 (27 %)** |
| Enriched    | 16/30 (53 %) | **18/30 (60 %)** | 8/30 (27 %) | 8/30 (27 %) |

**Netto-Bilanz Blind:** 5 GAIN (Heiligenfigur, Hacke, Peitsche, Schachtel, Spardose), 2 LOSE (Trog, Marmoraufsatz) → **+3 Top-Match**.
**Netto-Bilanz Enriched:** 4 GAIN (Heiligenfigur, Schachtel, Marmoraufsatz, Spardose), 2 LOSE (Tintenzeug, Nähschatulle) → **+2 Top-Match**.

v2 ist in beiden Modi besser als v1. Die Gewinne liegen genau in den Mustern, die wir im Prompt angesprochen haben. Die Verluste sind alles Grenzfälle ohne explizite Regel.

---

## Judge-Run über Iteration 2 (handverlesene 8 Objekte)

**Datum:** 2026-04-11
**Modell:** `gemini-3.1-pro-preview`
**Judge-Prompt:** `system_judge.txt` v1.0
**Selection:** `data/json/judge_selection.json` — 8 Objekte aus der Sample-Phase, Mischung aus Zickzack-Mismatches, Regel-Gewinnen, Sammlungs-Quirk-Kandidaten und Kontroll-Treffern.
**Kosten:** €0.029 für 8 Calls (rund €0.004 pro Judge-Call)

### Judge-Treffergenauigkeit

Der Judge wurde nicht gebeten, selbst zu klassifizieren, gibt aber in `judge_top_id` an, was er wählen würde. **8 von 8** Judge-Top-Wahlen stimmen mit dem Original überein — ein deutlich stärkeres Signal als das Flash-Lite-Modell in den Workflows A und B. Bemerkenswert, weil der Judge nur Text + Bild sieht, ohne Stage-1/Stage-2-Constraint.

### Verdict-Verteilung (8 Objekte)

| Verdict | Anzahl | Beispiele |
|---------|--------|-----------|
| `both_correct` | 3 | Spardose, Zither, Heiligenfigur |
| `tie_plausible` | 3 | Trog, Totschläger, Gürtel |
| `enriched_better` | 1 | Marmoraufsatz |
| `blind_better` | 1 | Spritze |
| `both_wrong` | 0 | — |

### Sammlungs-Quirks

**3 von 8** Objekte als `is_collection_quirk = true` markiert: Trog (`1169812`), Spritze (`1174037`), Totschläger (`1183673`). Das ist der didaktisch wichtigste Befund: bei mehr als einem Drittel der untersuchten Mismatches ist die KI nicht falsch, sondern die Sammlung hat eine nicht-offensichtliche Konvention (Spritze = Hollerschieße → Spielzeug, Totschläger = Fischtöter → Fischerei, Trog mit sammlungsinterner Kontext-Zuordnung).

### Beschreibungs-Qualität (1–5)

Mittelwert Blind: **4.5**, Mittelwert Enriched: **4.5**. Gleichauf, aber mit anderen Stärken: Enriched ist besser bei Konflikt-Detection, Blind besser bei nüchterner Zurückhaltung in mehrdeutigen Fällen (siehe Spritze: Blind schreibt vorsichtig „unbestimmtes Werkzeug", Enriched springt auf die Medizin-Assoziation).

### Hinweise aus den `prompt_improvement_hints`

Aggregiert über alle 8 Judge-Bewertungen. Diese sind die Grundlage für eine eventuelle Iteration 3.

1. **Enriched-Mode muss Metadaten-Klassifikation stärker priorisieren.** Mehrfach kritisiert (Trog, Spritze). Der Prompt sagt „nutze die Metadaten", aber nicht: „übernimm die Original-Top-Klassifikation, wenn ein klar benanntes Objekt vorliegt". Die KI kippt zurück auf visuelle Ersteinordnung.
2. **Homonym-Warnung für enriched.** „Spritze" kann Spielzeug (Hollerschieße) oder Medizin sein, „Totschläger" kann Waffe oder Fischereigerät sein. Der Prompt sollte explizit warnen, dass Objektnamen mehrdeutig sind und der Kontext aus der Sammlung die Lesart bestimmt.
3. **Inner-Merkmal-Regel:** die enriched-KI triggerte beim Spardose-Fall einen falschen Widerspruch („Leder ist nicht sichtbar"), obwohl das Original-Leder innen liegt und auf Außenaufnahmen naturgemäß nicht zu sehen ist. Der Prompt sollte die KI anweisen, dass Materialien, die in Metadaten nur für Innenbereiche stehen, keinen Widerspruch zum Außen-Bild darstellen.
4. **„Zubehör" vs. „Accessoires" im Vokabular unscharf.** Beim Gürtel markiert — eine konkrete Thesaurus-Mehrdeutigkeit, kein Prompt-Fehler.
5. **Blind-Mode zu schnell bei Kachelofen-Assoziation.** Beim Marmoraufsatz sprang Blind auf „Kachelofenteil", obwohl Material klar Stein ist. Spezifische Fallstudie, schwer generisch zu patchen.

### Offene Frage für Iteration 3

Lohnt sich eine Iteration 3, die Enriched explizit auf „Metadaten-Klassifikation priorisieren + Homonym-Warnung + Inner-Merkmal-Regel" tuned? Kosten: weitere ~€0.02 für Sample-Run + eventuell weiterer Judge-Run auf Teilmenge. Aber: v2 ist schon gut genug für den Vollauf, die Iterations-3-Gewinne wären Grenzfälle. Entscheidung mit User.

**Entscheidung:** Iteration 3 wird **nicht** umgesetzt. Die v2-Akkuranz ist für die Workshop-Story ausreichend, die zu erwartenden Iterations-3-Gewinne liegen in Grenzfällen, und weitere Judge-Runs kosten Gemini-Pro-Credits für marginalen Mehrwert. Stattdessen: Vollauf mit v2.0 auf der kompletten Selektion.

---

## Vollauf auf 245 Objekten (Prompt v2.0)

**Datum:** 2026-04-11
**Modell:** `gemini-3.1-flash-lite-preview`
**Prompts:** `system_blind.txt` v2.0, `system_enriched.txt` v2.0 (unverändert gegenüber Iteration 2)
**Selektion:** 245 Objekte (nach Entfernen von `1168643`, siehe Journal-Eintrag *Objekt 1168643 aus dem Scope entfernt*)

### Akkuranz

|             | Top-Match | Leaf-Match |
|-------------|-----------|------------|
| Blind       | 123/245 (**50 %**) | 62/245 (**25 %**) |
| Enriched    | 150/245 (**61 %**) | 85/245 (**35 %**) |

### Vergleich Sample (v2, n=30) → Vollauf (v2, n=245)

|             | Sample Top | Vollauf Top | Sample Leaf | Vollauf Leaf |
|-------------|-----------|-------------|-------------|--------------|
| Blind       | 53 %      | 50 %        | 27 %        | 25 %         |
| Enriched    | 60 %      | 61 %        | 27 %        | **35 %**     |

**Beobachtung:** Blind-Top fällt um 3 Punkte, Enriched-Top bleibt praktisch identisch. Bei der Leaf-Granularität ist der Sample stabil für Blind, aber **leicht pessimistisch** für Enriched — im Vollauf schneidet Enriched-Leaf 8 Punkte besser ab. Bei n=30 vs. n=245 ist das Sample statistisch schwach, und die Erkenntnis „Sample hat Enriched-Leaf unterschätzt" ist ehrlich ohne Überinterpretation: die v2-Prompt-Verbesserungen wirken bei der größeren Menge kumulativ etwas stärker, als der kleine Sample zeigte.

### Status

- Vollauf **abgeschlossen**, finale KI-Outputs liegen in `data/json/ai_blind.json` und `data/json/ai_enriched.json`.
- Judge-Daten unverändert: 8 handverlesene Objekte aus der Sample-Phase (siehe Judge-Run-Sektion oben).
- Iteration 3 **nicht umgesetzt** (siehe Entscheidung oben).
