"""
splitter - the Student Expense Splitter package.

UNIT II (Modules & Packages): this folder is a package because it has an
__init__.py. app.py imports from it with `from splitter import ...`.

    exceptions.py  custom exception classes          (Unit IV)
    validators.py  regex + date validation           (Unit I, III)
    models.py      User / Room class hierarchy       (Unit II)
    storage.py     JSON read/write + CSV export      (Unit IV)
    services.py    business logic used by routes     (Unit I, II)
    analytics.py   Pandas/NumPy summary + Matplotlib (Unit III, V)
"""
from .exceptions import SplitterError
from .services import RoomService
from .storage import JSONStorage, export_expenses_csv

__all__ = ["SplitterError", "RoomService", "JSONStorage", "export_expenses_csv"]
