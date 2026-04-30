from __future__ import annotations

from datetime import datetime

from game.state import Difficulty, GameState


def keypad_solution(state: GameState) -> str:
    """THE JOURNEY: HHMM dell'orologio. WITHOUT_ESCAPE: la codifica ascii del nome del giocatore senza zeri."""
    if state.difficulty == Difficulty.THE_JOURNEY:
        now = datetime.now()
        return f"{now.hour:02d}{now.minute:02d}"
    return ascii_code_without_zeros(state.player_name)


def ascii_code_without_zeros(name: str) -> str:
    """Concatenate ord digits, strip '0', take meaningful code (max 6 digits)."""
    raw = "".join(str(ord(c)) for c in name)
    stripped = raw.replace("0", "")
    if not stripped:
        return "1"
    # 6 cifre
    if len(stripped) > 6:
        return stripped[-6:]
    return stripped


def keypad_max_attempts(state: GameState) -> int:
    return 1 if state.difficulty == Difficulty.WITHOUT_ESCAPE else 2


def click_precision_required(state: GameState) -> float:
    return 0.80 if state.difficulty == Difficulty.WITHOUT_ESCAPE else 0.65


def time_multiplier(state: GameState) -> float:
    return 0.5 if state.difficulty == Difficulty.WITHOUT_ESCAPE else 1.0


def click_round_duration(state: GameState) -> float:
    """Leggermente più generoso in THE JOURNEY."""
    base = 14.0
    return base * time_multiplier(state)
