from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from game.state import GameState


def story_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "story.json"


# lingua di degault: "it" o "en"
# default language: "it" or "en"
_LANG = "it"


def set_language(lang: str) -> None:
    global _LANG
    _LANG = lang if lang in ("it", "en") else "it"


def load_story(lang: str | None = None) -> dict[str, Any]:
    # choose file based on language: use story_en.json for English, fallback to story.json
    root = Path(__file__).resolve().parent.parent / "data"
    if lang == "en":
        p = root / "story_en.json"
        if not p.is_file():
            p = root / "story.json"
    else:
        p = root / "story.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _check_show_if(state: GameState, show_if: str | None) -> bool:
    if not show_if:
        return True
    # simple boolean flags
    if show_if == "group_mode":
        return state.group_mode
    if show_if == "isolated_mode":
        return state.isolated_mode
    if show_if == "not_group":
        return not state.group_mode

    # trust thresholds: mirei_2, kenji_1, etc.
    m = re.match(r"^(mirei|kenji)_(\d+)$", show_if)
    if m:
        who, thr = m.group(1), int(m.group(2))
        if who == "mirei":
            return state.trust_mirei >= thr
        if who == "kenji":
            return state.trust_kenji >= thr

    # flag:NAME
    if show_if.startswith("flag:"):
        return bool(state.flags.get(show_if[5:]))

    # comparisons: ATTR OP NUMBER, e.g. tension>=3
    # this is needed for some choices
    m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*(<=|>=|==|!=|<|>)\s*(\-?\d+)$", show_if)
    if m:
        attr, op, sval = m.group(1), m.group(2), int(m.group(3))
        val = getattr(state, attr, None)
        if val is None:
            return False
        try:
            if op == ">=":
                return val >= sval
            if op == "<=":
                return val <= sval
            if op == ">":
                return val > sval
            if op == "<":
                return val < sval
            if op == "==":
                return val == sval
            if op == "!=":
                return val != sval
        except Exception:
            return False

    # unknown show_if condition, default to False to hide the choice
    return True


def visible_choices(state: GameState, node: dict[str, Any]) -> list[dict[str, Any]]:
    choices = node.get("choices") or []
    return [c for c in choices if _check_show_if(state, c.get("show_if"))]


def get_node(story: dict[str, Any], node_id: str) -> dict[str, Any]:
    nodes = story.get("nodes") or {}
    if node_id not in nodes:
        if _LANG == "en":
            return {
                "text": f"[Missing node: {node_id}]",
                "choices": [{"text": "Return to menu", "next": "intro_letter"}],
            }
        return {
            "text": f"[Nodo mancante: {node_id}]",
            "choices": [{"text": "Torna al menu", "next": "intro_letter"}],
        }
    return nodes[node_id]


def apply_choice_effects(state: GameState, choice: dict[str, Any]) -> None:
    effects = choice.get("effects") or []
    if isinstance(effects, str):
        effects = [effects]
    state.apply_effects(list(effects))
