from __future__ import annotations

from dataclasses import dataclass

from game.state import GameState

@dataclass(frozen=True) #dataclass 
class Trophy:
    id: str
    title: str
    description: str


TROPHIES: list[Trophy] = [
    Trophy("first_step", "First step", "You called the number."),
    Trophy("helpless", "Helpless", "Ending: HELPLESS."),
    Trophy("capsule_refuse", "Conscious Refusal", "You refused the capsule."),
    Trophy("allies", "Not Alone", "You befriended Evelyn and Artemis."),
    Trophy("lone_wolf", "Lone Wolf", "You chose to remain alone."),
    Trophy("fragments", "Three Lights", "You collected all fragments."),
    Trophy("corrupted", "Touched by Corruption", "You gained corruption."),
    Trophy("door_master", "The Rule", "You opened the reinforced door."),
    Trophy("return_without_escape", "Return without escape", "Ending: RETURN WITHOUT ESCAPE."),
    Trophy("refused", "Defied the Guards", "You refused the guards."),
    Trophy("survivor_click", "Precision", "You passed the click sequence."),
    Trophy("astral_prison", "Astral Prison", "Ending 3."),
    Trophy("lost_with_them", "Lost with Them", "Ending 4."),
    Trophy("escape_real", "Escape", "Ending 5."),
    Trophy("true_distortion", "True Distortion", "Ending 6."),
    Trophy("reset_end", "Reset", "Ending 7: RESET."),
    Trophy("secret_path", "Doctor's Secret", "The Doctor's secret."),
    Trophy("freefall_survivor", "Controlled Fall", "You completed a Free Fall."),
    Trophy("mirei_pact", "Mirei's Pact", "Ending with Mirei."),
    Trophy("kenji_merge", "Kenji Merge", "Ending with Kenji."),
    Trophy("betrayal_echo", "Echo of Betrayal", "Betrayal ending."),
    Trophy("act3_echo", "The Echoes", "You reached Act III."),
    Trophy("act4_tribunal", "Tribunal", "You reached Act IV."),
    # nuovi trofei per statistiche e allocazione
    Trophy("allocated_stats", "Initial Choices", "You assigned the initial stat points."),
    Trophy("mirei_bond", "Mirei Bond", "You have at least 2 trust with Mirei."),
    Trophy("kenji_bond", "Kenji Bond", "You have at least 2 trust with Kenji."),
    Trophy("friendship_trust", "Strong Bonds", "You have at least 2 trust with both Evelyn and Artemis."),
    Trophy("high_trust", "Bond Builder", "You accumulated 6+ total trust points."),
    # espansioni & minigiochi
    Trophy("prequel_family", "Roots", "You explored the family and factory prequel scene."),
    Trophy("kenji_subplot", "Kenji's Secrets", "You explored Kenji's subplot."),
    Trophy("mirei_archive", "Mirei's Archive", "You explored Mirei's archive."),
    Trophy("evelyn_arc", "Evelyn's Story", "You viewed Evelyn's personal scene."),
    Trophy("artemis_arc", "Artemis' Story", "You viewed Artemis' personal scene."),
    Trophy("hospital_wing", "Hospital Wing", "You faced the moral test in the hospital wing."),
    Trophy("simon_master", "Sequence Master", "You completed the Simon/Memory minigame."),
    Trophy("stealth_shadow", "Silent Shadow", "You passed the stealth minigame."),
]


# traduzioni per i trofei (titolo + descrizione)
TRANSLATIONS: dict = {
    "it": {
        "first_step": {"title": "Primo passo", "description": "Hai chiamato il numero."},
        "helpless": {"title": "Senza scampo", "description": "Finale: SENZA SCAMPO."},
        "capsule_refuse": {"title": "Rifiuto consapevole", "description": "Hai rifiutato la capsula."},
        "allies": {"title": "Non solo", "description": "Hai fatto amicizia con Evelyn e Artemis."},
        "lone_wolf": {"title": "Lupo solitario", "description": "Hai scelto di restare da solo."},
        "fragments": {"title": "Tre luci", "description": "Hai raccolto tutti i frammenti."},
        "corrupted": {"title": "Toccato dalla corruzione", "description": "Hai acquisito corruzione."},
        "door_master": {"title": "La regola", "description": "Hai aperto la porta rinforzata."},
        "return_without_escape": {"title": "Ritorno senza fuga", "description": "Finale: RITORNO SENZA FUGA."},
        "refused": {"title": "Sfida alle guardie", "description": "Hai sfidato le guardie."},
        "survivor_click": {"title": "Precisione", "description": "Hai completato la sequenza di click."},
        "astral_prison": {"title": "Prigione astrale", "description": "Finale 3."},
        "lost_with_them": {"title": "Perso con loro", "description": "Finale 4."},
        "escape_real": {"title": "Fuga", "description": "Finale 5."},
        "true_distortion": {"title": "Vera distorsione", "description": "Finale 6."},
        "reset_end": {"title": "Reset", "description": "Finale 7: RESET."},
        "secret_path": {"title": "Segreto del Dottore", "description": "Il segreto del Dottore."},
        "freefall_survivor": {"title": "Caduta controllata", "description": "Hai completato la Caduta Libera."},
        "mirei_pact": {"title": "Patto con Mirei", "description": "Finale con Mirei."},
        "kenji_merge": {"title": "Fusione con Kenji", "description": "Finale con Kenji."},
        "betrayal_echo": {"title": "Eco del tradimento", "description": "Finale del tradimento."},
        "act3_echo": {"title": "Gli echi", "description": "Hai raggiunto l'Atto III."},
        "act4_tribunal": {"title": "Tribunale", "description": "Hai raggiunto l'Atto IV."},
        "allocated_stats": {"title": "Scelte iniziali", "description": "Hai assegnato i punti iniziali alle statistiche."},
        "mirei_bond": {"title": "Legame con Mirei", "description": "Hai almeno 2 punti di fiducia con Mirei."},
        "kenji_bond": {"title": "Legame con Kenji", "description": "Hai almeno 2 punti di fiducia con Kenji."},
        "friendship_trust": {"title": "Legami forti", "description": "Hai almeno 2 punti di fiducia sia con Evelyn che con Artemis."},
        "high_trust": {"title": "Costruttore di legami", "description": "Hai accumulato almeno 6 punti totali di fiducia."},
        "prequel_family": {"title": "Radici", "description": "Hai esplorato il prequel della famiglia e della fabbrica."},
        "kenji_subplot": {"title": "Segreti di Kenji", "description": "Hai esplorato la sottotrama di Kenji."},
        "mirei_archive": {"title": "Archivio di Mirei", "description": "Hai esplorato l'archivio di Mirei."},
        "evelyn_arc": {"title": "Storia di Evelyn", "description": "Hai visto la scena personale di Evelyn."},
        "artemis_arc": {"title": "Storia di Artemis", "description": "Hai visto la scena personale di Artemis."},
        "hospital_wing": {"title": "Ali dell'ospedale", "description": "Hai affrontato la prova morale nell'ala dell'ospedale."},
        "simon_master": {"title": "Maestro delle sequenze", "description": "Hai completato il minigioco Simon/Memoria."},
        "stealth_shadow": {"title": "Ombra silenziosa", "description": "Hai superato il minigioco furtivo."},
    }
}


def check_story_trophies(
    state: GameState,
    node_id: str,
    unlocked: set[str],
) -> list[str]:
    new: list[str] = []
    if node_id == "finale_helpless" and "helpless" not in unlocked:
        new.append("helpless")
    if node_id == "finale_capsule_refuse" and "capsule_refuse" not in unlocked:
        new.append("capsule_refuse")
    if node_id == "finale_return_factory" and "return_without_escape" not in unlocked:
        new.append("return_without_escape")
    if (
        node_id == "area_distesa_intro"
        and state.group_mode
        and state.trust_evelyn > 0
        and state.trust_artemis > 0
        and "allies" not in unlocked
    ):
        new.append("allies")
    if node_id == "area_distesa_intro" and state.isolated_mode and "lone_wolf" not in unlocked:
        new.append("lone_wolf")
    if state.fragments_collected >= 3 and "fragments" not in unlocked:
        new.append("fragments")
    if state.corruption > 0 and "corrupted" not in unlocked:
        new.append("corrupted")
    if node_id == "institute_room" and "door_master" not in unlocked:
        new.append("door_master")
    if node_id == "custodi_click_minigame" and "refused" not in unlocked:
        new.append("refused")
    if state.flags.get("click_minigame_won") and "survivor_click" not in unlocked:
        new.append("survivor_click")
    if node_id == "called_number" and "first_step" not in unlocked:
        new.append("first_step")
    if node_id == "act5_secret_doctor" and "secret_path" not in unlocked:
        new.append("secret_path")
    if node_id == "finale_astral_prison" and "astral_prison" not in unlocked:
        new.append("astral_prison")
    if node_id == "finale_lost_with_them" and "lost_with_them" not in unlocked:
        new.append("lost_with_them")
    if node_id == "finale_escape" and "escape_real" not in unlocked:
        new.append("escape_real")
    if node_id == "finale_true_distortion" and "true_distortion" not in unlocked:
        new.append("true_distortion")
    if node_id == "finale_reset" and "reset_end" not in unlocked:
        new.append("reset_end")
    if node_id == "finale_mirei_pact" and "mirei_pact" not in unlocked:
        new.append("mirei_pact")
    if node_id == "finale_kenji_merge" and "kenji_merge" not in unlocked:
        new.append("kenji_merge")
    if node_id == "finale_betrayal_echo" and "betrayal_echo" not in unlocked:
        new.append("betrayal_echo")
    if node_id == "act3_echo_intro" and "act3_echo" not in unlocked:
        new.append("act3_echo")
    if node_id == "act4_threshold" and "act4_tribunal" not in unlocked:
        new.append("act4_tribunal")
    if node_id in (
        "finale_astral_prison",
        "finale_lost_with_them",
        "finale_escape",
        "finale_true_distortion",
    ) and "freefall_survivor" not in unlocked:
        new.append("freefall_survivor")

    # statistics 
    if state.flags.get("allocated_stats") and "allocated_stats" not in unlocked:
        new.append("allocated_stats")
    if state.trust_mirei >= 2 and "mirei_bond" not in unlocked:
        new.append("mirei_bond")
    if state.trust_kenji >= 2 and "kenji_bond" not in unlocked:
        new.append("kenji_bond")
    if state.trust_evelyn >= 2 and state.trust_artemis >= 2 and "friendship_trust" not in unlocked:
        new.append("friendship_trust")
    if (state.trust_evelyn + state.trust_artemis + state.trust_mirei + state.trust_kenji) >= 6 and "high_trust" not in unlocked:
        new.append("high_trust")
    # espansioni & minigiochi
    if node_id == "prequel_end" and "prequel_family" not in unlocked:
        new.append("prequel_family")
    if state.flags.get("kenji_subplot_done") and "kenji_subplot" not in unlocked:
        new.append("kenji_subplot")
    if state.flags.get("mirei_archive_done") and "mirei_archive" not in unlocked:
        new.append("mirei_archive")
    if state.flags.get("evelyn_arc_seen") and "evelyn_arc" not in unlocked:
        new.append("evelyn_arc")
    if state.flags.get("artemis_arc_seen") and "artemis_arc" not in unlocked:
        new.append("artemis_arc")
    if state.flags.get("hospital_helped") and "hospital_wing" not in unlocked:
        new.append("hospital_wing")
    if state.flags.get("simon_won") and "simon_master" not in unlocked:
        new.append("simon_master")
    if state.flags.get("stealth_won") and "stealth_shadow" not in unlocked:
        new.append("stealth_shadow")
    return new


def all_trophy_dicts(unlocked: set[str], language: str = "en") -> list[dict]:
    """Return trophy dicts localized according to `language` (default 'en').

    Keeps the original English text as fallback if a translation is missing.
    """
    tr_map = TRANSLATIONS.get(language, {})
    out: list[dict] = []
    for t in TROPHIES:
        tr = tr_map.get(t.id)
        if tr:
            title = tr.get("title", t.title)
            description = tr.get("description", t.description)
        else:
            title = t.title
            description = t.description
        out.append({
            "id": t.id,
            "title": title,
            "description": description,
            "unlocked": t.id in unlocked,
        })
    return out
