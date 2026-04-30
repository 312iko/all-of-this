from __future__ import annotations
# statistiche del giocatore e flags di gioco
import re
from dataclasses import dataclass, field
from enum import Enum # enum are types of data classes, used for fixed sets of values (like difficulty levels)
from typing import Any


class Difficulty(str, Enum):
    THE_JOURNEY = "the_journey"
    WITHOUT_ESCAPE = "without_escape"


@dataclass
class GameState:
    player_name: str = "PLAYER"
    difficulty: Difficulty = Difficulty.THE_JOURNEY
    # language code: 'it' or 'en'
    language: str = "it"
    trust_evelyn: int = 0
    trust_artemis: int = 0
    trust_mirei: int = 0
    trust_kenji: int = 0
    # player statistics (allocable at start)
    strength: int = 0
    kindness: int = 0
    stubbornness: int = 0
    isolated_mode: bool = False
    corruption: int = 0
    group_mode: bool = False
    fragments_collected: int = 0
    tension: int = 0
    clues: list[str] = field(default_factory=list)
    act: int = 1
    playtime_seconds: float = 0.0
    current_node: str = "intro_letter"
    flags: dict[str, Any] = field(default_factory=dict)

    def apply_effects(self, effects: list[str]) -> None:
        for raw in effects:
            raw = raw.strip()
            if not raw:
                continue
            if raw.startswith("trust_evelyn"):
                self.trust_evelyn += self._trust_delta("trust_evelyn", raw)
            elif raw.startswith("trust_artemis"):
                self.trust_artemis += self._trust_delta("trust_artemis", raw)
            elif raw.startswith("trust_mirei"):
                self.trust_mirei += self._trust_delta("trust_mirei", raw)
            elif raw.startswith("trust_kenji"):
                self.trust_kenji += self._trust_delta("trust_kenji", raw)
            elif raw.startswith("strength"):
                self.strength += self._trust_delta("strength", raw)
            elif raw.startswith("kindness"):
                self.kindness += self._trust_delta("kindness", raw)
            elif raw.startswith("stubbornness"):
                self.stubbornness += self._trust_delta("stubbornness", raw)
            elif raw == "corruption+1" or raw == "corruption +":
                self.corruption += 1
            elif raw == "isolated_mode":
                self.isolated_mode = True
                self.group_mode = False
            elif raw == "group_mode":
                self.group_mode = True
                self.isolated_mode = False
            elif raw.startswith("set:"):
                key, _, val = raw[4:].partition("=")
                self._set_flag(key.strip(), val.strip())
            elif raw.startswith("fragments:"):
                n = int(raw.split(":", 1)[1])
                self.fragments_collected = max(0, min(3, n))
            elif raw.startswith("act:"):
                self.act = int(raw.split(":", 1)[1])
            elif raw.startswith("clue:"):
                c = raw[5:].strip()
                if c and c not in self.clues:
                    self.clues.append(c)
            elif raw == "tension+1":
                self.tension += 1
            elif raw == "memory_fragment":
                self.flags["memory_fragment"] = True

    @staticmethod
    def _trust_delta(prefix: str, s: str) -> int:
        rest = s[len(prefix) :]
        m = re.match(r"^\+(\d+)$", rest)
        if m:
            return int(m.group(1))
        m = re.match(r"^-(\d+)$", rest)
        if m:
            return -int(m.group(1))
        return 0

    def _set_flag(self, key: str, val: str) -> None:
        if val.lower() in ("true", "1", "yes"):
            self.flags[key] = True
        elif val.lower() in ("false", "0", "no"):
            self.flags[key] = False
        else:
            try:
                self.flags[key] = int(val)
            except ValueError:
                self.flags[key] = val

    def to_json_dict(self) -> dict:
        return {
            "player_name": self.player_name,
            "difficulty": self.difficulty.value,
            "language": self.language,
            "trust_evelyn": self.trust_evelyn,
            "trust_artemis": self.trust_artemis,
            "trust_mirei": self.trust_mirei,
            "trust_kenji": self.trust_kenji,
            "strength": self.strength,
            "kindness": self.kindness,
            "stubbornness": self.stubbornness,
            "isolated_mode": self.isolated_mode,
            "corruption": self.corruption,
            "group_mode": self.group_mode,
            "fragments_collected": self.fragments_collected,
            "tension": self.tension,
            "clues": list(self.clues),
            "act": self.act,
            "playtime_seconds": self.playtime_seconds,
            "current_node": self.current_node,
            "flags": dict(self.flags),
        }

    @classmethod
    def from_json_dict(cls, d: dict) -> GameState:
        diff = Difficulty(d.get("difficulty", Difficulty.THE_JOURNEY.value))
        return cls(
            player_name=d.get("player_name", "PLAYER"),
            language=d.get("language", "it"),
            difficulty=diff,
            trust_evelyn=int(d.get("trust_evelyn", 0)),
            trust_artemis=int(d.get("trust_artemis", 0)),
            trust_mirei=int(d.get("trust_mirei", 0)),
            trust_kenji=int(d.get("trust_kenji", 0)),
            strength=int(d.get("strength", 0)),
            kindness=int(d.get("kindness", 0)),
            stubbornness=int(d.get("stubbornness", 0)),
            isolated_mode=bool(d.get("isolated_mode", False)),
            corruption=int(d.get("corruption", 0)),
            group_mode=bool(d.get("group_mode", False)),
            fragments_collected=int(d.get("fragments_collected", 0)),
            tension=int(d.get("tension", 0)),
            clues=list(d.get("clues") or []),
            act=int(d.get("act", 1)),
            playtime_seconds=float(d.get("playtime_seconds", 0.0)),
            current_node=d.get("current_node", "intro_letter"),
            flags=dict(d.get("flags") or {}),
        )
