"""
models.py - Domain classes: User, Member, Room, EqualSplitRoom, CustomSplitRoom.

UNIT II (OOP):
  * Encapsulation: attributes such as _code and _members are "private" by
    convention and exposed read-only through @property.
  * Inheritance: EqualSplitRoom and CustomSplitRoom both extend Room.
  * Polymorphism: each subclass overrides share_for_slot(), so the rest of
    the code calls room.share_for(...) without caring which kind of room it is.
  * Dunder methods: __len__ and __repr__.

UNIT II (Functional programming): lambda, map, filter and next() are used to
query members (unpaid members, paid members, member names).

UNIT III (Dates): datetime records join/payment/dissolve timestamps.

Rule used throughout: total_people INCLUDES the owner. The owner paid the full
bill upfront, so the owner counts as paid from the start (a 5-person room
starts at "1/5 paid" and dissolves at "5/5 paid").
"""
from datetime import datetime

from .exceptions import (
    AlreadyPaidError,
    NotAMemberError,
    OwnerCannotJoinError,
    RoomFullError,
    ValidationError,
)

ROLE_OWNER = "owner"
ROLE_PARTICIPANT = "participant"


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


class User:
    """A student using the app. Tracks how many rooms they created for default naming."""

    def __init__(self, username, created_at=None, rooms_created=0):
        self._username = username
        self._created_at = created_at or now_iso()
        self._rooms_created = int(rooms_created)

    @property
    def username(self):
        return self._username

    @property
    def rooms_created(self):
        return self._rooms_created

    def next_default_room_name(self):
        """Spotify-style default name: 'Room #1', 'Room #2', ..."""
        return f"Room #{self._rooms_created + 1}"

    def register_room_created(self):
        self._rooms_created += 1

    def to_dict(self):
        return {
            "username": self._username,
            "created_at": self._created_at,
            "rooms_created": self._rooms_created,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)          # keyword-argument unpacking

    def __repr__(self):
        return f"User({self._username!r}, rooms_created={self._rooms_created})"


class Member:
    """A participant who joined a room (not the owner)."""

    def __init__(self, username, joined_at=None, paid=False, paid_at=None):
        self.username = username
        self.joined_at = joined_at or now_iso()
        self.paid = bool(paid)
        self.paid_at = paid_at

    def mark_paid(self):
        if self.paid:
            raise AlreadyPaidError()
        self.paid = True
        self.paid_at = now_iso()

    def to_dict(self):
        return {
            "username": self.username,
            "joined_at": self.joined_at,
            "paid": self.paid,
            "paid_at": self.paid_at,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class Room:
    """Base class. Subclasses decide how the bill is split (share_for_slot)."""

    SPLIT_TYPE = "base"

    def __init__(self, code, owner, activity, date, total_amount, total_people, name,
                 created_at=None, members=None, dissolved_at=None):
        if int(total_people) < 2:
            raise ValidationError("A room needs at least 2 people.")
        self._code = code
        self._owner = owner
        self.name = name
        self.activity = activity
        self.date = date
        self._total_amount = round(float(total_amount), 2)
        self._total_people = int(total_people)
        self.created_at = created_at or now_iso()
        self.dissolved_at = dissolved_at
        self._members = [m if isinstance(m, Member) else Member.from_dict(m) for m in (members or [])]

    # ---------- read-only properties (encapsulation) ----------
    @property
    def code(self):
        return self._code

    @property
    def owner(self):
        return self._owner

    @property
    def total_amount(self):
        return self._total_amount

    @property
    def total_people(self):
        return self._total_people

    @property
    def members(self):
        return tuple(self._members)        # tuple: callers cannot append to it

    @property
    def participant_slots(self):
        return self._total_people - 1      # everyone except the owner

    # ---------- polymorphic split logic ----------
    def share_for_slot(self, slot):
        """Amount owed by the participant in position `slot` (0-based join order)."""
        raise NotImplementedError("Subclasses must implement share_for_slot()")

    @property
    def owner_share(self):
        others = sum(map(self.share_for_slot, range(self.participant_slots)))
        return round(self._total_amount - others, 2)

    def share_for(self, username):
        """Share for any user: owner, existing member, or the next person to join."""
        if username == self._owner:
            return self.owner_share
        for index, member in enumerate(self._members):
            if member.username == username:
                return self.share_for_slot(index)
        if self.is_full:
            return None
        return self.share_for_slot(len(self._members))

    # ---------- functional-style queries ----------
    def find_member(self, username):
        return next(filter(lambda m: m.username == username, self._members), None)

    def paid_members(self):
        return list(filter(lambda m: m.paid, self._members))

    def unpaid_members(self):
        return list(filter(lambda m: not m.paid, self._members))

    def member_names(self):
        return list(map(lambda m: m.username, self._members))

    def collected_amount(self):
        return round(sum(self.share_for_slot(i) for i, m in enumerate(self._members) if m.paid), 2)

    def outstanding_amount(self):
        return round(self._total_amount - self.owner_share - self.collected_amount(), 2)

    # ---------- status ----------
    @property
    def paid_count(self):
        return 1 + len(self.paid_members())        # +1 for the owner

    @property
    def progress(self):
        return f"{self.paid_count}/{self._total_people} paid"

    @property
    def is_full(self):
        return len(self._members) >= self.participant_slots

    @property
    def is_dissolved(self):
        return self.paid_count >= self._total_people

    def role_of(self, username):
        if username == self._owner:
            return ROLE_OWNER
        if self.find_member(username):
            return ROLE_PARTICIPANT
        return None

    def is_active_for(self, username):
        """Owner: active until everyone pays. Participant: active until they pay."""
        if username == self._owner:
            return not self.is_dissolved
        member = self.find_member(username)
        return member is not None and not member.paid

    # ---------- actions ----------
    def add_member(self, username):
        if username == self._owner:
            raise OwnerCannotJoinError()
        existing = self.find_member(username)
        if existing:
            if existing.paid:
                raise AlreadyPaidError()
            return existing                    # re-entering the code is harmless
        if self.is_full:
            raise RoomFullError(f"Room {self._code} already has all {self._total_people} people.")
        member = Member(username)
        self._members.append(member)
        return member

    def mark_paid(self, username):
        if username == self._owner:
            raise OwnerCannotJoinError()
        member = self.find_member(username)
        if member is None:
            raise NotAMemberError()
        member.mark_paid()
        if self.is_dissolved and not self.dissolved_at:
            self.dissolved_at = now_iso()
        return member

    # ---------- persistence ----------
    def to_dict(self):
        return {
            "code": self._code,
            "owner": self._owner,
            "name": self.name,
            "activity": self.activity,
            "date": self.date,
            "total_amount": self._total_amount,
            "total_people": self._total_people,
            "split_type": self.SPLIT_TYPE,
            "created_at": self.created_at,
            "dissolved_at": self.dissolved_at,
            "members": [m.to_dict() for m in self._members],
        }

    def __len__(self):
        return len(self._members)

    def __repr__(self):
        return f"{type(self).__name__}({self._code!r}, {self.name!r}, {self.progress})"


class EqualSplitRoom(Room):
    """Everyone pays total / people. Any rounding paisa is absorbed by the owner."""

    SPLIT_TYPE = "equal"

    def share_for_slot(self, slot):
        return round(self._total_amount / self._total_people, 2)


class CustomSplitRoom(Room):
    """Owner types each participant's share (in join order); owner keeps the remainder."""

    SPLIT_TYPE = "custom"

    def __init__(self, *args, custom_shares=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._custom_shares = [round(float(s), 2) for s in (custom_shares or [])]
        if len(self._custom_shares) != self.participant_slots:
            raise ValidationError(
                f"Enter exactly {self.participant_slots} custom shares (one per person other than you)."
            )
        if any(share <= 0 for share in self._custom_shares):
            raise ValidationError("Every custom share must be more than ₹0.")
        if sum(self._custom_shares) > self._total_amount:
            raise ValidationError("Custom shares add up to more than the total amount.")

    def share_for_slot(self, slot):
        return self._custom_shares[slot]

    def to_dict(self):
        data = super().to_dict()           # reuse parent logic, then extend it
        data["custom_shares"] = list(self._custom_shares)
        return data


ROOM_TYPES = {cls.SPLIT_TYPE: cls for cls in (EqualSplitRoom, CustomSplitRoom)}


def room_from_dict(data):
    """Factory: builds the right subclass from saved JSON."""
    data = dict(data)
    split_type = data.pop("split_type", "equal")
    room_class = ROOM_TYPES.get(split_type)
    if room_class is None:
        raise ValidationError(f"Unknown split type: {split_type}")
    return room_class(**data)
