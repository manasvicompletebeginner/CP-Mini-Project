# Student Expense Splitter

One student pays the whole bill, creates a room, and shares a 6-character code. Friends join with the code, see what they owe, and tap **Paid**. The owner watches progress live (`2/5 paid`). When everyone has paid, the room moves to **Previous Rooms**, where Pandas, NumPy and Matplotlib turn past rooms into spending analytics.

## Setup and run

```bash
pip install -r requirements.txt        # flask, numpy, pandas, matplotlib
python seed_demo.py                    # optional: sample data (replaces rooms_data.json)
python app.py
```

Open http://127.0.0.1:5000

**Demo with two students:** the username is stored per browser tab. Open two tabs, log in as `riya` in one and `aman` in the other. Create a room in one tab, join it from the other, tap Paid, and watch the owner's progress update within 5 seconds.

## Rules the app follows

- `total_people` includes the owner. The owner paid upfront, so a 5-person room starts at `1/5 paid` and dissolves at `5/5 paid`.
- Blank room name → `Room #N`, where N counts all rooms that owner has ever created.
- Equal split: each person pays `total_amount / total_people`; the owner absorbs any rounding paisa.
- Custom split: owner enters one share per participant, in join order. The owner's share is whatever is left.
- A participant's room leaves **My Rooms** the moment they tap Paid. The owner's room leaves when everyone has paid.

## Project structure

```
expense_splitter/
├── app.py                 Flask routes (GET/POST, JSON in/out)       Unit V
├── seed_demo.py           Sample data for the lab demo
├── rooms_data.json        JSON "database"                            Unit IV
├── requirements.txt
├── splitter/              Python package                             Unit II
│   ├── __init__.py
│   ├── exceptions.py      Custom exception classes                   Unit IV
│   ├── validators.py      Regex + datetime validation                Unit I, III
│   ├── models.py          User, Member, Room → Equal/CustomSplitRoom Unit II
│   ├── storage.py         JSON read/write, CSV export                Unit IV
│   ├── services.py        Business logic used by the routes          Unit I, II
│   └── analytics.py       Pandas/NumPy summary, Matplotlib chart     Unit III, V
├── templates/index.html   Single-page UI
├── static/style.css
├── static/app.js          fetch() calls to the API
└── exports/               CSV files land here
```

## Syllabus map (where to point during viva)

| Unit | Concept | Where |
|---|---|---|
| I | Default / keyword arguments | `generate_room_code(existing, length=6, alphabet=...)`, `validate_amount(value, field=..., minimum=...)`, `create_room(..., room_name="", split_type="equal")` |
| I | List, tuple, dict, set | `rooms_for_user()` returns a tuple; `Room.members` returns a tuple; `set(rooms)` for unique codes; dict comprehensions in `_load()` / `_save()` |
| I | Loops, conditionals | `for room in mine` in `rooms_for_user()`; status branches in `serialize_room()` |
| II | Classes, encapsulation | `models.py`: `_code`, `_members` exposed via `@property` |
| II | Inheritance, polymorphism | `EqualSplitRoom` and `CustomSplitRoom` override `share_for_slot()`; `CustomSplitRoom.to_dict()` calls `super()` |
| II | `lambda`, `map`, `filter` | `Room.unpaid_members()`, `paid_members()`, `member_names()`, `owner_share`; owner-only filter in `rooms_for_user()` |
| II | Modules / packages | `splitter/` package with `__init__.py` |
| III | Regex | `validators.py`: room code `^[A-Z0-9]{6}$`, username, amount, date, `re.split` for custom shares |
| III | Dates | `datetime.strptime` rejects `2026-02-30`; `timedelta` caps future dates; timestamps via `datetime.now()` |
| III | NumPy | `analytics.summarize()`: `np.sum`, `np.mean`, `np.median`, `np.max`, `np.std` |
| III | Pandas | `build_expense_frame()` DataFrame; boolean filtering `df[df["role"] == "owner"]`; `groupby().agg()` by activity and month |
| IV | JSON files | `storage.JSONStorage.load()` / `save()` |
| IV | CSV | `storage.export_expenses_csv()` with `csv.DictWriter` |
| IV | Custom exceptions | `exceptions.py`: `InvalidRoomCodeError`, `RoomFullError`, `AlreadyPaidError`, `RoomNotFoundError`, `NotAMemberError`, `OwnerCannotJoinError`, `ValidationError`, `StorageError` |
| IV | `try / except / finally` | `JSONStorage.load()` closes the file in `finally` |
| V | Flask routes, request, JSON | `app.py`: `request.get_json()`, `request.args`, `jsonify`, `@app.errorhandler` |
| V | Matplotlib | `analytics.spending_chart_png()` served at `/api/users/<u>/chart.png` |

## REST API

| Method | Route | Body / query | Purpose |
|---|---|---|---|
| POST | `/api/login` | `{username}` | Register or log in |
| POST | `/api/rooms` | `{username, room_name?, activity, date, total_amount, total_people, split_type?, custom_shares?}` | Create room |
| GET | `/api/rooms/<code>` | `?username=` | Room details for a viewer |
| POST | `/api/rooms/<code>/join` | `{username}` | Join room |
| POST | `/api/rooms/<code>/pay` | `{username}` | Mark paid |
| GET | `/api/users/<u>/rooms` | `?owner_only=true` | `{active, previous}` |
| GET | `/api/users/<u>/summary` | | Analytics JSON |
| GET | `/api/users/<u>/chart.png` | | Matplotlib chart |
| GET | `/api/users/<u>/export.csv` | | Past expenses CSV |

Errors come back as JSON, e.g. `409 {"error": "RoomFullError", "message": "..."}`.

## Suggested split for a 4-person group

| Member | Owns | Explains |
|---|---|---|
| 1 | `models.py`, `exceptions.py` | OOP, inheritance, polymorphism, lambda/map/filter, custom exceptions |
| 2 | `validators.py`, `storage.py`, `services.py` | Regex, dates, JSON + CSV file handling, try/except/finally |
| 3 | `analytics.py` | NumPy, Pandas groupby/filtering, Matplotlib |
| 4 | `app.py`, `templates/`, `static/` | Flask routes, GET/POST, JSON, fetch-based frontend |
