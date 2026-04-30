from __future__ import annotations

from game.state import GameState


def secret_ending_eligible(state: GameState) -> bool:
    # eligibility for secret ending: fragments, memory, key clues + protocol (Act IV), trust, shadows not ignored
    clues = set(state.clues)
    need_base = {"fear", "exit_fake", "monitoring"}
    protocol_ok = "protocol" in clues or state.flags.get("saw_core_truth")
    trust_ok = (
        state.trust_evelyn >= 2
        or state.trust_artemis >= 2
        or state.trust_mirei >= 2
    )
    return (
        state.fragments_collected >= 3
        and state.flags.get("memory_fragment")
        and need_base.issubset(clues)
        and protocol_ok
        and trust_ok
        and not state.flags.get("ignored_shadows")
    )


def capture_variant(state: GameState) -> bool:
    # capture / abyss variant. Capture if score >= 4, otherwise abyss.
    score = 0
    if state.isolated_mode:
        score += 3
    score += state.corruption * 2
    if state.trust_evelyn + state.trust_artemis <= 0:
        score += 2
    if state.flags.get("custodi_click_failed"):
        score += 3
    if state.flags.get("ignored_shadows"):
        score += 2
    if state.tension >= 3:
        score += 1
    if state.trust_mirei <= -1:
        score += 1
    if state.flags.get("act4_betrayed"):
        score += 2
    return score >= 4


def resolve_finale_entry(state: GameState) -> str:
    # final node depends on secret ending eligibility and capture variant
    if secret_ending_eligible(state):
        return "act5_secret_doctor"
    if capture_variant(state):
        return "act5_variant_a_intro"
    return "act5_variant_b_intro"


def freefall_target_units(state: GameState) -> float:
    from game.state import Difficulty

    if state.difficulty == Difficulty.WITHOUT_ESCAPE:
        return 2400.0
    return 560.0
