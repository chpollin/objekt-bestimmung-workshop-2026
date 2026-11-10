---
title: Handoff
project:
  name: Objekt-Bestimmung Workshop 2026
  repository: https://github.com/chpollin/objekt-bestimmung-workshop-2026
method:
  name: Promptotyping
  url: https://dhcraft.org/Promptotyping/
status: active
created: 2026-11-10
updated: 2026-11-10
language: de
---

# Handoff

Wiedereinstieg in das ruhende Projekt. Der Workshop fand am 20.04.2026 statt, der Viewer ist unter https://chpollin.github.io/objekt-bestimmung-workshop-2026/ veröffentlicht. Einstieg ist [README.md](README.md), danach [requirements.md](requirements.md).

## Judge-Restdateien

- Received: 2026-11-10, Repository-Pflege
- Source: `git log -- data/json/judge_selection.json data/json/ai_judge_selection.json`, Journal-Eintrag vom 2026-04-20
- Target: `data/json/`, `_archive/`
- Context: Die beiden Überreste des entfernten Judge-Workflows werden von keinem Skript und nicht von `app.js` gelesen. Sie sind seit dem WIP-Commit `33b6451` vom 2026-07-19 versioniert und über GitHub Pages abrufbar. Das Journal hatte sie am 2026-04-20 noch als untracked geführt und die Entscheidung offen gelassen.
- Operator point: Entscheiden, ob die Dateien gelöscht, nach `_archive/` gelegt oder belassen werden.
