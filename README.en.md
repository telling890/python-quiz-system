# Python Quiz System

[![CI](https://github.com/telling890/python-quiz-system/actions/workflows/selftest.yml/badge.svg)](https://github.com/telling890/python-quiz-system/actions/workflows/selftest.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-3776AB.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D4.svg)](#)

A desktop quiz app for the lab exercises of *Python Programming* (chapters 3–5):
write code, press `F5`, and every built-in test case is checked instantly — passing
questions are recorded, failures go to the wrong-answer book automatically.

> 中文说明见 [README.md](README.md)

## Download

**[Python-quiz-system-portable.zip](https://github.com/telling890/python-quiz-system/releases/latest)** — unzip, then double-click `Python刷题系统.exe`.
No Python installation, no network, no admin rights required.

Or clone the repo and run `dist/Python刷题系统/Python刷题系统.exe` directly.

## Features

- **139 questions / 338 test cases** across 5 chapters: program control (35), sequences (17),
  strings (17), extra exercises (40), intro algorithms (30)
- **Judge engine**: sandboxed in-process execution, 6-second timeout watchdog, normalized output
  comparison (raw mode keeps leading spaces for ASCII-art questions), categorized error hints,
  blocked dangerous calls
- **Learning loop**: wrong-answer book, favourites, statistics with pie charts and a score trend line,
  automatic progress and code saving
- **Mock exams**: pick question count / chapters / difficulty / time limit; chapter-balanced or
  weak-spot-weighted paper generation; countdown, answer-hiding, graded result report with
  per-question detail
- **Extras**: keyword search (`Ctrl+F`), CSV export of the study report, custom question bank import (JSON)
- **Packaging**: PyInstaller `--onedir` build (no `%TEMP%` extraction), ~21 MB folder / ~9 MB zip

## Run from source

```bash
python main.py        # requires Python 3.8+, stdlib + Tkinter only
python selftest.py    # question bank self-test (139 questions / 338 cases)
python _test_exam.py  # exam system self-test (12 checks)
python _interact.py   # UI interaction smoke test (15 checks)
```

## Build the exe

```bash
python -m pip install --target pylibs -r requirements-build.txt
python build.py
```

Output: `dist/Python刷题系统/` plus `dist/Python刷题系统-便携版.zip`.
Do **not** switch to `--onefile`: the single-file bootloader extracts to `%TEMP%` and fails on
some machines.

## Repo layout

```
├─ main.py / ui.py / ui_exam.py / widgets.py / theme.py   UI
├─ judge.py                                              judge engine
├─ exam.py                                               paper generation & scoring
├─ qbank.py / bank_*.py                                  question bank (5 chapters)
├─ store.py                                              progress persistence
├─ docs/                                                 requirements, design, test report,
│                                                         slides, project report (PDF included)
├─ dist/Python刷题系统/                                   ready-to-run build
└─ shots/                                                screenshots & demo gif
```

## Docs

Requirements, design, test report, defence slides and project report are in `docs/`
(Chinese). PDF versions live in `docs/pdf/` and render directly on GitHub.

## Licence

[MIT](LICENSE)
