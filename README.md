# sap-xep-tkb: volunteer–child tutoring scheduler

**English** · [Tiếng Việt](README.vi.md)

A local, offline scheduling tool built for **SUGAR Vietnam**, a volunteer tutoring program for children living at two social protection centres in Vietnam. Every week the coordinators have to match volunteer teachers with children by subject, grade, free days and pairing rules. Before this tool, they did it by hand in a spreadsheet. The app turns that spreadsheet into a constraint model, solves it with **Google OR-Tools CP-SAT**, and writes the timetable back to Excel in the same layout the coordinators already use. The coordinators treat the output as a first draft and adjust it by hand for personal constraints the model does not capture.

> The repository contains **only synthetic sample data** (codes such as `TNV001`, `BE001`). Real volunteer and child data stay on the coordinator's machine and are excluded by `.gitignore`. The app uses no LLM or AI API and does no personality analysis.

## The problem

- Classes run Monday to Friday, 18:00–20:00, at two centres with different rules.
- Each session is one teacher, one subject and one or two children.
- A teacher must be registered for that exact subject **and grade**, be free that day, and stay under a weekly session limit.
- Two children can share a session only if the centre allows it (primary level, same centre, same known age by default) and they are not marked as an incompatible pair.
- Each centre needs a designated lead every day. At one centre the lead must also teach; at the other, being present is enough.
- Coordinators review volunteer–child pairs by hand (*Preferred / Normal / Do not pair*) and can lock sessions they have already agreed on.

With 18 volunteer teachers, a hand-made timetable has to be redone whenever one person changes their free days.

## How it works

```text
Excel workbook ──► excel_io: read, normalise, validate (errors reported by sheet and row)
                       │
                       ▼
               engine: enumerate legal sessions ──► CP-SAT model
                       │                               │
               policies: site, pairing, lead rules     ▼
                                       lexicographic optimisation
                                                   │
                                                   ▼
           export: per-centre timetable + unmet demands + full input ──► Excel
```

**Hard constraints** (never violated): subject–grade registration, free days, one session per person per day, weekly limits counted across both centres, "do not pair" ratings, incompatible child pairs, centre-specific lead rules, locked sessions.

**Objectives, optimised in strict order** rather than as a weighted sum, so that a lower priority can never outweigh a higher one:

1. number of children who get at least one session;
2. number of child–subject demands met;
3. (optional resource mode) fewer sessions taken by staff, so volunteers are used first;
4. number of *Preferred* pairs honoured;
5. fewer two-child sessions;
6. a balanced load across teachers (sum of squared session counts).

Each objective is fixed only after CP-SAT proves it optimal, then the next one is solved. The default time budget is 30 seconds. On timeout the app returns the best valid schedule found and says that it may not be optimal.

**When a full schedule is impossible**, the app still shows every session it could place. That partial schedule is marked **BẢN TẠM** (draft) and comes with a `Yeu_cau_chua_dat` sheet that lists each unmet demand and the checks that failed (no teacher for that grade, no shared free day, a blocked pair, …). The explanation lists likely causes. It does not claim a single exact cause for a global conflict.

## Features

- Streamlit interface in Vietnamese, running on `127.0.0.1` only.
- Pair review screen: shows interview answers and notes for a volunteer–child pair and stores the coordinator's rating. Notes are shown to people, never parsed by the solver.
- Lock a session, re-solve around it, or unlock it. Conflicting locks are reported, not silently dropped.
- Edit volunteers and staff in the app: free days, subjects per grade, session limits, lead eligibility.
- Optional rules per centre and per person: fixed teacher for a child–subject, specialist-only subjects, subjects a person cannot teach, a flag for children from international schools, chemistry → integrated science flexibility.
- Excel export with one colour-coded timetable sheet per centre (children as rows, weekdays as columns, plus the lead team), along with detailed sheets that can be loaded again next week.

## Quick start (Windows)

Requires Python 3.11+ (3.12 recommended).

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Or double-click `run_app.bat`. Then open <http://127.0.0.1:8501> and choose **dữ liệu mẫu** (sample data) to try it.

The sample workbook `data/du_lieu_mau.xlsx` has 6 volunteers, 9 children and 14 demands. Two demands are unsatisfiable on purpose: `BE008` has no teacher for its grade and `BE009` shares no free day with anyone.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The suite covers the scheduling rules, objective order, conflicting locks, under-resourced weeks, a zero time budget, Excel validation and round-trips, and the main UI flow (solve → lock → re-solve → block a pair). At the last validation run (9 October 2026), 61 tests passed.

## Project layout

```text
app.py                     Streamlit interface
staff_ui.py                volunteer / staff editing screens
scheduler/models.py        data model
scheduler/excel_io.py      workbook reading, normalisation and validation
scheduler/policies.py      centre, pairing and lead rules
scheduler/engine.py        candidate sessions and CP-SAT model
scheduler/explanations.py  reasons for unmet demands
scheduler/export.py        timetable tables and Excel export
scheduler/staff_editing.py edits to volunteer and staff records
scripts/sample_data.py     synthetic data generator
tests/                     pytest suite
```

The full workbook format (every sheet and column) is documented in Vietnamese in [README.vi.md](README.vi.md#cấu-trúc-workbook).

## Limitations

- One fixed time slot per day. No rooms, holidays, calendar dates or multi-week planning.
- Each child–subject demand means one session per week.
- No login, database or multi-user editing. Progress is saved as an Excel file.
- With many children of the same age and subject, the number of candidate sessions grows quickly and large inputs may hit the time limit before optimality is proven.

## Author

Built by [Phan Xuân Khoa](https://github.com/s4dz) for the SUGAR Vietnam coordinating team, where he coordinates the volunteer teachers.
