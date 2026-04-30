from __future__ import annotations

from dataclasses import dataclass

from game.state import GameState

# codex entries, unlocked based on flags, clues, trust, act, etc. Each entry has an id, category, and unlock condition. Data for each entry is stored in separate dicts for Italian and English.
@dataclass(frozen=True)
class CodexEntry:
    id: str
    category: str
    unlock_flag: str

ENTRIES = [
    CodexEntry("shinamihu_city", "world", "flag:seen_shinamihu"),
    CodexEntry("the_doctor", "characters", "flag:met_doctor"),
    CodexEntry("the_protocol", "experiment", "clue:protocol"),
    CodexEntry("astral_plane", "experiment", "act:>=2"),
    CodexEntry("evelyn", "characters", "trust_evelyn>=1"),
    CodexEntry("artemis", "characters", "trust_artemis>=1"),
    CodexEntry("mirei", "characters", "trust_mirei>=1"),
    CodexEntry("kenji", "characters", "trust_kenji>=1"),
    CodexEntry("memory_fragments", "experiment", "flag:memory_fragment"),
    CodexEntry("custodi", "experiment", "flag:met_custodi"),
    CodexEntry("factory", "world", "clue:work_history"),
    CodexEntry("corruption", "experiment", "corruption>=1"),
]


DATA_IT: dict[str, dict[str, str]] = {
    "shinamihu_city": {
        "title": "ShinaMihu",
        "text": (
            "Citta industriale nel cuore del Giappone, avvolta da una nebbia perenne.\n"
            "Quartieri operai, fabbriche LED, insegne al neon sbiadite.\n"
            "Qui il tempo sembra non passare — solo consumare."
        ),
    },
    "the_doctor": {
        "title": "Il Dottore",
        "text": (
            "Direttore del Programma Sperimentale Privato.\n"
            "Camice bianco, maschera chirurgica nera, sguardo stanco.\n"
            "Non e un semplice ricercatore: e un sopravvissuto di una versione precedente dell'esperimento.\n"
            "Ha costruito il piano astrale per non farsi piu trovare dalla sua stessa mente."
        ),
    },
    "the_protocol": {
        "title": "Il Protocollo",
        "text": (
            "Sistema di monitoraggio e controllo che gestisce il piano astrale.\n"
            "Non e IA nel senso tradizionale: e un framework di analisi comportamentale\n"
            "collegato a parametri fisiologici reali.\n"
            "Il suo nome segreto nel codice non e amore. E continuita."
        ),
    },
    "astral_plane": {
        "title": "Piano Astrale",
        "text": (
            "Dimensione costruita dalla mente dei soggetti sotto neuro-esposizione.\n"
            "Qui la coscienza non si limita a osservare: costruisce, ricorda, si difende.\n"
            "Reagisce alla paura come protocollo — non in modo umano.\n"
            "I frammenti di memoria sono ancora che tengono il soggetto connesso alla realta."
        ),
    },
    "evelyn": {
        "title": "Evelyn",
        "text": (
            "Capelli biondi, occhi stanchi.\n"
            "Finita nel programma per debiti di gioco e prestiti.\n"
            "Ha un senso dell'umorismo che nasconde la paura.\n"
            "Cerca connessione perche ha perso tutto il resto."
        ),
    },
    "artemis": {
        "title": "Artemis",
        "text": (
            "Postura da modello, sguardo duro.\n"
            "Truffa contrattuale, carriera mai decollata, dignita smontata pezzo per pezzo.\n"
            "Non sorride mai per primo. Preferisce la rabbia alla resa."
        ),
    },
    "mirei": {
        "title": "Mirei",
        "text": (
            "Catalogatrice del piano astrale. Non un medico, non un dottore.\n"
            "Quella che registra cio che il sistema vorrebbe dimenticare.\n"
            "Paga in tempo, non in denaro. Sa piu di quanto dice.\n"
            "Offre patti — ma il prezzo e sempre la liberta."
        ),
    },
    "kenji": {
        "title": "Kenji",
        "text": (
            "Tecnico di campo. Morto nel mondo reale, ma la sua attenzione\n"
            "e rimasta incollata al protocollo.\n"
            "Parla attraverso schermi rotti. Sa che l'errore non classificato\n"
            "e cio che rompe il modello — ed e per questo che lo temono."
        ),
    },
    "memory_fragments": {
        "title": "Frammenti di Memoria",
        "text": (
            "Tre schegge di ricordo rubato che attenuano l'influenza del Dottore.\n"
            "Non servono al sistema — servono al soggetto.\n"
            "Se raccolti tutti, aprono un passaggio verso la verita del protocollo.\n"
            "Ogni frammento e un'ancora alla realta."
        ),
    },
    "custodi": {
        "title": "I Custodi",
        "text": (
            "Figure in uniformi scure con visiere opache.\n"
            "Non medici, non poliziotti — guardiani di un confine.\n"
            "La loro presenza segna il punto di non ritorno:\n"
            "accettare di essere scortati via o resistere."
        ),
    },
    "factory": {
        "title": "La Fabbrica",
        "text": (
            "Fabbrica di componenti LED a ShinaMihu.\n"
            "Straordinari non pagati, contratti a scadenza lampo,\n"
            "capi che chiamano i lavoratori 'risorsa'.\n"
            "E da qui che tutto e iniziato."
        ),
    },
    "corruption": {
        "title": "Corruzione",
        "text": (
            "Effetto collaterale del piano astrale sui soggetti.\n"
            "Ogni atto di violenza, ogni frammento corrotto, ogni scelta sbagliata\n"
            "lascia un residuo. La corruzione non e solo numerica:\n"
            "e la prova che il piano sta cambiando chi lo abita."
        ),
    },
}


DATA_EN: dict[str, dict[str, str]] = {
    "shinamihu_city": {
        "title": "ShinaMihu",
        "text": (
            "Industrial city in the heart of Japan, shrouded in perpetual fog.\n"
            "Working-class neighborhoods, LED factories, faded neon signs.\n"
            "Time seems not to pass here — only consume."
        ),
    },
    "the_doctor": {
        "title": "The Doctor",
        "text": (
            "Director of the Private Experimental Program.\n"
            "White coat, black surgical mask, tired eyes.\n"
            "Not just a researcher: a survivor of a previous version of the experiment.\n"
            "He built the astral plane so his own mind could never find him again."
        ),
    },
    "the_protocol": {
        "title": "The Protocol",
        "text": (
            "Monitoring and control system managing the astral plane.\n"
            "Not AI in the traditional sense: a behavioral analysis framework\n"
            "linked to real physiological parameters.\n"
            "Its secret name in the code is not love. It is continuity."
        ),
    },
    "astral_plane": {
        "title": "Astral Plane",
        "text": (
            "A dimension built by the subjects' minds under neuro-exposure.\n"
            "Here consciousness doesn't just observe — it builds, remembers, defends itself.\n"
            "It reacts to fear like a protocol — not in a human way.\n"
            "Memory fragments are anchors keeping the subject connected to reality."
        ),
    },
    "evelyn": {
        "title": "Evelyn",
        "text": (
            "Blonde hair, tired eyes.\n"
            "Entered the program due to gambling debts and loans.\n"
            "Hides her fear behind a sense of humor.\n"
            "Seeks connection because she's lost everything else."
        ),
    },
    "artemis": {
        "title": "Artemis",
        "text": (
            "Model's posture, hard stare.\n"
            "Contractual fraud, career never took off, dignity dismantled piece by piece.\n"
            "Never smiles first. Prefers anger to surrender."
        ),
    },
    "mirei": {
        "title": "Mirei",
        "text": (
            "Cataloger of the astral plane. Not a doctor, not a scientist.\n"
            "The one who records what the system wants to forget.\n"
            "Pays in time, not money. Knows more than she says.\n"
            "Offers pacts — but the price is always freedom."
        ),
    },
    "kenji": {
        "title": "Kenji",
        "text": (
            "Field technician. Dead in the real world, but his attention\n"
            "remained glued to the protocol.\n"
            "Speaks through broken screens. Knows that the unclassified error\n"
            "is what breaks the model — and that's why they fear it."
        ),
    },
    "memory_fragments": {
        "title": "Memory Fragments",
        "text": (
            "Three shards of stolen memory that attenuate the Doctor's influence.\n"
            "Not useful to the system — useful to the subject.\n"
            "If all collected, they open a passage to the protocol's truth.\n"
            "Each fragment is an anchor to reality."
        ),
    },
    "custodi": {
        "title": "The Custodi",
        "text": (
            "Figures in dark uniforms with opaque visors.\n"
            "Not doctors, not police — guardians of a boundary.\n"
            "Their presence marks the point of no return:\n"
            "accept being escorted away or resist."
        ),
    },
    "factory": {
        "title": "The Factory",
        "text": (
            "LED component factory in ShinaMihu.\n"
            "Unpaid overtime, short-term contracts,\n"
            "bosses who call workers 'resources'.\n"
            "This is where everything began."
        ),
    },
    "corruption": {
        "title": "Corruption",
        "text": (
            "Side effect of the astral plane on subjects.\n"
            "Every act of violence, every corrupted fragment, every wrong choice\n"
            "leaves a residue. Corruption isn't just numerical:\n"
            "it's proof the plane is changing those who inhabit it."
        ),
    },
}


def _check_unlock(entry: CodexEntry, state: GameState) -> bool:
    flag = entry.unlock_flag
    if flag.startswith("flag:"):
        return bool(state.flags.get(flag[5:]))
    if flag.startswith("clue:"):
        return flag[5:] in state.clues
    if flag.startswith("act:"):
        op_val = flag[4:]
        if op_val.startswith(">="):
            return state.act >= int(op_val[2:])
        if op_val.startswith(">"):
            return state.act > int(op_val[1:])
        if op_val.startswith("=="):
            return state.act == int(op_val[2:])
    m = __import__("re").match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*(>=|<=|==|!=|<|>)\s*(\-?\d+)$", flag)
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
    return False


def get_unlocked_entries(state: GameState) -> list[CodexEntry]:
    return [e for e in ENTRIES if _check_unlock(e, state)]


def get_entry_data(entry: CodexEntry, language: str = "it") -> dict[str, str]:
    data = DATA_IT if language == "it" else DATA_EN
    return data.get(entry.id, {"title": entry.id, "text": "???"})
