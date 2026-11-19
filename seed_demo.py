"""
seed_demo.py - Fills rooms_data.json with sample data for the lab demo.

WARNING: this REPLACES rooms_data.json.
Run:  python seed_demo.py   then log in as riya, aman, neha or kabir.
"""
import os

from splitter import JSONStorage, RoomService

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "rooms_data.json")

if os.path.exists(DATA_FILE):
    os.remove(DATA_FILE)

service = RoomService(JSONStorage(DATA_FILE))
friends = ["riya", "aman", "neha", "kabir"]
for name in friends:
    service.login(name)

# (owner, activity, date, total, people, room_name, payers)
past_rooms = [
    ("riya", "Dinner at Haldiram's", "2026-08-14", 1600, 4, "", ["aman", "neha", "kabir"]),
    ("aman", "Movie night", "2026-08-30", 1200, 4, "PVR Saturday", ["riya", "neha", "kabir"]),
    ("riya", "Cab to Noida", "2026-09-05", 450, 3, "", ["aman", "neha"]),
    ("neha", "Fest tickets", "2026-09-21", 2000, 4, "Moksha passes", ["riya", "aman", "kabir"]),
    ("kabir", "Dinner at Haldiram's", "2026-10-03", 1400, 4, "", ["riya", "aman", "neha"]),
    ("riya", "Project printouts", "2026-10-18", 360, 4, "", ["aman", "neha", "kabir"]),
]
for owner, activity, date, total, people, name, payers in past_rooms:
    room = service.create_room(owner, activity, date, total, people, room_name=name)
    for payer in payers:
        service.join_room(room["code"], payer)
        service.pay(room["code"], payer)

# Active rooms, partly paid
active = service.create_room("riya", "Goa trip deposit", "2026-11-15", 8000, 5, room_name="Goa 2026")
service.join_room(active["code"], "aman")
service.pay(active["code"], "aman")
service.join_room(active["code"], "neha")          # joined but not paid yet

custom = service.create_room("aman", "Birthday cake", "2026-11-18", 1000, 3,
                             split_type="custom", custom_shares="300, 300")
service.join_room(custom["code"], "riya")

print("Demo data written to rooms_data.json")
print(f"  Active room (riya owns, 2/5 paid): {active['code']}")
print(f"  Custom split room (aman owns, riya owes ₹300): {custom['code']}")
print("  Log in as: " + ", ".join(friends))
