"""Guard: esper event names come from GameEvent, never from a bare literal.

An event name is a wire between a ``dispatch_event`` and a ``set_handler``
that nothing else connects. Spelled as two independent string literals, a
typo on either end is a silent no-op — the event is dispatched and simply
never arrives. Routing every name through ``config.enums.GameEvent`` turns
that into an AttributeError at import time.
"""

import re
from pathlib import Path

from config.enums import GameEvent

ROOT = Path(__file__).resolve().parent.parent
PROD_ROOTS = ["core", "game", "bootstrap.py", "main.py"]

# dispatch_event("x") / set_handler("x") / remove_handler("x") /
# requests.on("x") / requests.modal("x") — the first argument is the wire.
LITERAL_CALL = re.compile(r"\b(dispatch_event|set_handler|remove_handler|on|modal)\(\s*[\"']")


def _prod_files() -> list[Path]:
    files: list[Path] = []
    for entry in PROD_ROOTS:
        path = ROOT / entry
        files.extend([path] if path.is_file() else sorted(path.rglob("*.py")))
    return files


def test_no_bare_event_name_literals() -> None:
    offenders = []
    for path in _prod_files():
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if LITERAL_CALL.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")
    assert not offenders, "event names must be GameEvent members:\n" + "\n".join(offenders)


def test_every_event_member_is_used() -> None:
    """A member nobody dispatches is a dead wire — delete it or wire it up."""
    sources = "\n".join(p.read_text() for p in _prod_files())
    unused = [e.name for e in GameEvent if f"GameEvent.{e.name}" not in sources]
    assert not unused, f"GameEvent members never used in production code: {unused}"


def test_members_are_plain_strings_for_esper() -> None:
    """esper keys its handler registry by the raw name — str-compat is load-bearing."""
    for event in GameEvent:
        assert event == event.value
        assert hash(event) == hash(event.value)
