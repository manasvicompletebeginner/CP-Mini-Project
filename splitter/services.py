"""
services.py - Business logic that the Flask routes call.

UNIT I: default + keyword arguments, lists, tuples, dicts, sets, loops,
        conditionals, list/dict comprehensions.
UNIT II: uses the Room class hierarchy polymorphically; lambda/filter/sorted.
UNIT IV: raises custom exceptions (RoomNotFoundError etc.).
"""
import secrets
import string
import threading

from .exceptions import RoomNotFoundError, ValidationError
from .models import ROLE_OWNER, ROOM_TYPES, User, room_from_dict
from .validators import (
    parse_custom_shares,
    validate_amount,
    validate_date,
    validate_people,
    validate_room_code,
    validate_text,
    validate_username,
)

CODE_ALPHABET = string.ascii_uppercase + string.digits


def generate_room_code(existing_codes, length=6, alphabet=CODE_ALPHABET):
    """Random code like 'K7Q2ZD' that is not already in the set `existing_codes`."""
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(length))
        if code not in existing_codes:
            return code


class RoomService:
    def __init__(self, storage):
        self._storage = storage
        self._lock = threading.Lock()     # one write at a time (Flask can run threaded)

    # ---------- load / save ----------
    def _load(self):
        data = self._storage.load()
        rooms = {code: room_from_dict(raw) for code, raw in data["rooms"].items()}
        users = {name: User.from_dict(raw) for name, raw in data["users"].items()}
        return rooms, users

    def _save(self, rooms, users):
        self._storage.save({
            "rooms": {code: room.to_dict() for code, room in rooms.items()},
            "users": {name: user.to_dict() for name, user in users.items()},
        })

    @staticmethod
    def _find_room(rooms, code):
        room = rooms.get(code)
        if room is None:
            raise RoomNotFoundError(f"No room found with code {code}.")
        return room

    # ---------- serialising a room for one viewer ----------
    @staticmethod
    def serialize_room(room, viewer=None):
        role = room.role_of(viewer) if viewer else None
        member = room.find_member(viewer) if viewer else None

        if role == ROLE_OWNER:
            status, closed_at = ("closed" if room.is_dissolved else "collecting"), room.dissolved_at
        elif member:
            status, closed_at = ("paid" if member.paid else "unpaid"), member.paid_at
        else:
            status, closed_at = "not_joined", None

        data = {
            "code": room.code,
            "name": room.name,
            "activity": room.activity,
            "date": room.date,
            "owner": room.owner,
            "total_amount": room.total_amount,
            "total_people": room.total_people,
            "split_type": room.SPLIT_TYPE,
            "paid_count": room.paid_count,
            "progress": room.progress,
            "is_dissolved": room.is_dissolved,
            "slots_left": room.participant_slots - len(room),
            "role": role,
            "status": status,
            "my_share": room.share_for(viewer) if viewer else None,
            "closed_at": closed_at,
            "created_at": room.created_at,
        }
        if role == ROLE_OWNER:
            data["collected"] = room.collected_amount()
            data["outstanding"] = room.outstanding_amount()
            data["members"] = [
                {"username": m.username, "paid": m.paid, "share": room.share_for_slot(i), "paid_at": m.paid_at}
                for i, m in enumerate(room.members)
            ]
        return data

    # ---------- public API ----------
    def login(self, username):
        username = validate_username(username)
        with self._lock:
            rooms, users = self._load()
            is_new = username not in users
            if is_new:
                users[username] = User(username)
                self._save(rooms, users)
        return {"username": username, "new_user": is_new}

    def create_room(self, owner, activity, date, total_amount, total_people,
                    room_name="", split_type="equal", custom_shares=None):
        owner = validate_username(owner)
        activity = validate_text(activity, field="Activity")
        room_name = validate_text(room_name, field="Room name", required=False)
        date = validate_date(date)
        total_amount = validate_amount(total_amount)
        total_people = validate_people(total_people)
        if split_type not in ROOM_TYPES:
            raise ValidationError(f"Split type must be one of: {', '.join(ROOM_TYPES)}.")

        with self._lock:
            rooms, users = self._load()
            user = users.setdefault(owner, User(owner))
            room_args = {
                "code": generate_room_code(set(rooms)),     # set of existing codes
                "owner": owner,
                "name": room_name or user.next_default_room_name(),
                "activity": activity,
                "date": date,
                "total_amount": total_amount,
                "total_people": total_people,
            }
            if split_type == "custom":
                room_args["custom_shares"] = parse_custom_shares(custom_shares)

            room = ROOM_TYPES[split_type](**room_args)       # polymorphic constructor
            user.register_room_created()
            rooms[room.code] = room
            self._save(rooms, users)
        return self.serialize_room(room, owner)

    def get_room(self, code, viewer=None):
        code = validate_room_code(code)
        viewer = validate_username(viewer) if viewer else None
        rooms, _ = self._load()
        return self.serialize_room(self._find_room(rooms, code), viewer)

    def join_room(self, code, username):
        code = validate_room_code(code)
        username = validate_username(username)
        with self._lock:
            rooms, users = self._load()
            room = self._find_room(rooms, code)
            room.add_member(username)
            users.setdefault(username, User(username))
            self._save(rooms, users)
        return self.serialize_room(room, username)

    def pay(self, code, username):
        code = validate_room_code(code)
        username = validate_username(username)
        with self._lock:
            rooms, users = self._load()
            room = self._find_room(rooms, code)
            room.mark_paid(username)
            self._save(rooms, users)
        return self.serialize_room(room, username)

    def rooms_for_user(self, username, owner_only=False):
        """Returns a tuple: (active_rooms, previous_rooms)."""
        username = validate_username(username)
        rooms, _ = self._load()

        mine = [room for room in rooms.values() if room.role_of(username)]
        if owner_only:
            mine = list(filter(lambda room: room.owner == username, mine))

        active, previous = [], []
        for room in mine:
            target = active if room.is_active_for(username) else previous
            target.append(self.serialize_room(room, username))

        active.sort(key=lambda r: (r["date"], r["created_at"]), reverse=True)
        previous.sort(key=lambda r: r["closed_at"] or r["date"], reverse=True)
        return active, previous
