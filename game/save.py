from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from game.state import Difficulty, GameState

SAVE_VERSION = 2

SAVES_DIR = Path(__file__).resolve().parent.parent / "saves"
LEGACY_SAVE = Path(__file__).resolve().parent.parent / "save_data.json"

# directory for saves, e.g. saves/slot1.json, saves/slot2.json, etc.
def saves_dir() -> Path:
    return SAVES_DIR

# per slot: saves/slot1.json, slot2.json, slot3.json
def slot_path(slot: int) -> Path:
    if slot not in (1, 2, 3):
        slot = 1
    SAVES_DIR.mkdir(parents=True, exist_ok=True)
    return SAVES_DIR / f"slot{slot}.json"

# in WITHOUT_ESCAPE, loading is disabled to prevent save scumming
def can_load(state: GameState) -> bool:
    return state.difficulty != Difficulty.WITHOUT_ESCAPE

# in WITHOUT_ESCAPE, saving is disabled to prevent save scumming
def save_game(
    state: GameState,
    trophies_unlocked: list[str],
    slot: int = 1,
    path: Path | None = None,
) -> None:
    p = path or slot_path(slot)
    payload: dict[str, Any] = {
        "version": SAVE_VERSION,
        "slot": slot,
        "state": state.to_json_dict(),
        "trophies_unlocked": list(trophies_unlocked),
    }
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")

# returns (GameState, trophies_unlocked) or None if no valid save found
def load_game(path: Path | None = None, slot: int | None = None) -> tuple[GameState, list[str]] | None:
    if path is not None:
        candidates = [path]
    elif slot is not None:
        candidates = [slot_path(slot)]
    else:
        candidates = [LEGACY_SAVE]

    for p in candidates:
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        st = GameState.from_json_dict(data.get("state") or {})
        tro = list(data.get("trophies_unlocked") or [])
        return st, tro

    return None


def slot_has_save(slot: int) -> bool:
    return slot_path(slot).is_file()


def slot_preview(slot: int) -> str | None:
    loaded = load_game(slot=slot)
    if not loaded:
        return None
    st, _ = loaded
    # localize preview based on saved language
    if getattr(st, "language", "it") == "en":
        return f"Act {st.act} — {st.current_node[:28]}…"
    return f"Atto {st.act} — {st.current_node[:28]}…"
