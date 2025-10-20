from pathlib import Path

def _write_theme(base: str):
    Path(".streamlit").mkdir(exist_ok=True)
    if base == "dark":
        theme = """[theme]
base="dark"
primaryColor="#22d3ee"
backgroundColor="#0b0f17"
secondaryBackgroundColor="#111827"
textColor="#e5e7eb"
font="sans serif"
"""
    else:
        theme = """[theme]
base="light"
primaryColor="#0ea5e9"
backgroundColor="#ffffff"
secondaryBackgroundColor="#f6f9fc"
textColor="#0f172a"
font="sans serif"
"""
    Path(".streamlit/config.toml").write_text(theme, encoding="utf-8")
    st.rerun()

import streamlit as st
import random, csv, os, re
from io import StringIO

st.set_page_config(page_title="German A1 Vocab Trainer", page_icon="🇩🇪")
st.title("🇩🇪 German A1 Vocab Trainer")
import os

# Simple password gate (set APP_PASSWORD in env / Secrets)
if "authed" not in st.session_state:
    st.session_state.authed = False

if not st.session_state.authed:
    pwd = st.text_input("Password", type="password")
    if st.button("Enter"):
        if pwd and pwd == os.getenv("APP_PASSWORD", ""):
            st.session_state.authed = True
        else:
            st.error("Wrong password")
    st.stop()

# ---------- Deck I/O ----------
DEFAULT_CARDS = [
    {"en":"Hello","de":"Hallo"},
    {"en":"Goodbye","de":"Tschüss"},
    {"en":"Please","de":"Bitte"},
    {"en":"Thank you","de":"Danke"},
    {"en":"Excuse me / Sorry","de":"Entschuldigung"},
    {"en":"Yes","de":"Ja"},
    {"en":"No","de":"Nein"},
    {"en":"Water","de":"Wasser"},
    {"en":"Bread","de":"Brot"},
    {"en":"To speak","de":"Sprechen"},
]
DECK_PATH = "deck.csv"

def load_deck():
    cards = []
    if os.path.exists(DECK_PATH):
        with open(DECK_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                en = (row.get("en") or "").strip()
                de = (row.get("de") or "").strip()
                if en and de:
                    cards.append({"en": en, "de": de})
    if not cards:
        cards = DEFAULT_CARDS
    return cards

def save_new_card(en, de):
    exists = os.path.exists(DECK_PATH)
    with open(DECK_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["en","de"])
        if not exists:
            writer.writeheader()
        writer.writerow({"en":en, "de":de})

# ---------- Typing-mode tolerant checking ----------
ARTICLES = {"der","die","das","ein","eine","einen","einem","einer"}
UMLAUT_MAP = {"ä":"ae","ö":"oe","ü":"ue","ß":"ss"}

def strip_parentheses(s: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", s).strip()

def normalize(s: str) -> str:
    s = s.strip().lower()
    parts = s.split()
    if parts and parts[0] in ARTICLES:
        s = " ".join(parts[1:])
    for k,v in UMLAUT_MAP.items():
        s = s.replace(k, v)
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s

def levenshtein(a: str, b: str) -> int:
    if a == b: return 0
    if len(a) < len(b): a, b = b, a
    prev = list(range(len(b)+1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(cur[j-1]+1, prev[j]+1, prev[j-1]+(ca!=cb)))
        prev = cur
    return prev[-1]

def allowed_distance(n: int) -> int:
    if n <= 4: return 1
    if n <= 7: return 2
    return 3

def acceptable_variants(de_text: str):
    base = strip_parentheses(de_text)
    parts = re.split(r"\s*[/;,]\s*|\s+oder\s+", base)
    return [p for p in parts if p] or [base]

def check_answer(user_input: str, de_text: str):
    variants = acceptable_variants(de_text)
    user_n = normalize(user_input)
    if not user_n:
        return False, variants[0]
    for v in variants:
        v_n = normalize(v)
        if user_n == v_n:
            return True, v
        if levenshtein(user_n, v_n) <= allowed_distance(len(v_n)):
            return True, v
    return False, variants[0]

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Practice")
    practice_type = st.radio("Practice Type", ["Flashcards", "Typing", "Multiple Choice"], index=0)

    direction_flash = None
    direction_mc = None
    strict = False

    if practice_type == "Flashcards":
        direction_flash = st.radio("Direction (Flashcards)", ["English → German", "German → English"], index=0)
    elif practice_type == "Typing":
        strict = st.toggle("Strict checking (no typos allowed)", value=False)
    else:  # Multiple Choice
        direction_mc = st.radio("Direction (MC)", ["English → German", "German → English"], index=0)

    session_size = st.slider("Cards this session", 5, 200, 30, 5)

    st.divider()
    st.header("Add a word to deck")
    with st.form("add_word"):
        en_in = st.text_input("English")
        de_in = st.text_input("German (Deutsch)")
        if st.form_submit_button("Add"):
            if en_in and de_in:
                save_new_card(en_in.strip(), de_in.strip())
                st.success("Added to deck.csv!")
            else:
                st.error("Please fill both English and German.")

    st.divider()
    st.header("Export deck")
    _buf = StringIO()
    w = csv.DictWriter(_buf, fieldnames=["en","de"])
    w.writeheader()
    for c in load_deck():
        w.writerow(c)
    st.download_button("⬇️ Download deck.csv", _buf.getvalue().encode("utf-8"),
                       file_name="deck.csv", mime="text/csv")

# ---------- Load deck & session state ----------
CARDS = load_deck()
if "order" not in st.session_state:
    st.session_state.order = list(range(len(CARDS)))
if "i" not in st.session_state:
    st.session_state.i = 0
if "correct" not in st.session_state:
    st.session_state.correct = 0
if "show" not in st.session_state:
    st.session_state.show = False
if "answer_input" not in st.session_state:
    st.session_state.answer_input = ""
if "mc_i" not in st.session_state:
    st.session_state.mc_i = -1
if "mc_options" not in st.session_state:
    st.session_state.mc_options = []
if "mc_selected" not in st.session_state:
    st.session_state.mc_selected = None
if "mc_answer" not in st.session_state:
    st.session_state.mc_answer = None

def restart(shuffle=True):
    st.session_state.i = 0
    st.session_state.correct = 0
    st.session_state.show = False
    st.session_state.answer_input = ""
    st.session_state.order = list(range(len(CARDS)))
    st.session_state.mc_i = -1
    st.session_state.mc_options = []
    st.session_state.mc_selected = None
    st.session_state.mc_answer = None
    if shuffle:
        random.shuffle(st.session_state.order)

# ---------- Header controls ----------
left, right = st.columns(2)
with left:
    if st.button("Start / Restart"):
        restart(shuffle=True)
with right:
    st.write(f"Progress: {st.session_state.i} / {min(len(CARDS), session_size)}  |  ✅ {st.session_state.correct}")

# ---------- Helpers ----------
def make_mc_options(cards, idx, en_to_de=True, n_opts=4):
    """Return a list of options including the correct answer + distractors."""
    card = cards[idx]
    if en_to_de:
        correct = card["de"]
        pool = [c["de"] for c in cards if c is not card]
    else:
        correct = card["en"]
        pool = [c["en"] for c in cards if c is not card]

    # sample up to n_opts-1 unique distractors
    pool = list(dict.fromkeys(pool))  # dedupe while keeping order
    if len(pool) >= n_opts - 1:
        distractors = random.sample(pool, n_opts - 1)
    else:
        distractors = pool
    options = list({correct, *distractors})
    while len(options) < n_opts and pool:
        pick = random.choice(pool)
        if pick not in options:
            options.append(pick)
    random.shuffle(options)
    return options, correct

# ---------- Main loop ----------
finished = (st.session_state.i >= min(len(CARDS), session_size))
if finished:
    st.success(f"Done! Score: {st.session_state.correct} / {min(len(CARDS), session_size)}")
else:
    idx = st.session_state.order[st.session_state.i]
    card = CARDS[idx]

    if practice_type == "Flashcards":
        if direction_flash == "English → German":
            prompt, answer = card["en"], card["de"]
        else:
            prompt, answer = card["de"], card["en"]

        st.subheader(prompt)
        if st.button("Show answer", disabled=st.session_state.show):
            st.session_state.show = True
        if st.session_state.show:
            st.write(f"**Answer:** {answer}")
            c1, c2 = st.columns(2)
            if c1.button("✅ I knew it"):
                st.session_state.correct += 1
                st.session_state.i += 1
                st.session_state.show = False
            if c2.button("❌ Not yet"):
                st.session_state.i += 1
                st.session_state.show = False

    elif practice_type == "Typing":
        # Typing is EN → DE
        prompt, answer = card["en"], card["de"]
        st.subheader(prompt)

        st.text_input("Type the German word/phrase:", key="answer_input")
        cols = st.columns(3)
        with cols[0]:
            if st.button("Check"):
                ok, accepted = check_answer(st.session_state.answer_input, answer)
                # strict: exact (normalized) match only
                if strict:
                    ok = normalize(st.session_state.answer_input) == normalize(acceptable_variants(answer)[0])
                    accepted = acceptable_variants(answer)[0]
                if ok:
                    st.success(f"✅ Correct: {accepted}")
                    st.session_state.correct += 1
                    st.session_state.i += 1
                    st.session_state.answer_input = ""
                    st.session_state.show = False
                else:
                    st.info("Not quite — try again or reveal the answer.")
        with cols[1]:
            if st.button("Reveal"):
                st.session_state.show = True
        with cols[2]:
            if st.button("Skip"):
                st.session_state.i += 1
                st.session_state.answer_input = ""
                st.session_state.show = False

        if st.session_state.show:
            st.write(f"**Answer:** {answer}")

    else:  # Multiple Choice
        en_to_de = (direction_mc == "English → German")
        prompt = card["en"] if en_to_de else card["de"]
        answer = card["de"] if en_to_de else card["en"]
        st.subheader(prompt)

        # Generate options once per card
        if st.session_state.mc_i != st.session_state.i:
            opts, correct = make_mc_options(CARDS, idx, en_to_de=en_to_de, n_opts=4)
            st.session_state.mc_options = opts
            st.session_state.mc_answer = correct
            st.session_state.mc_selected = None
            st.session_state.mc_i = st.session_state.i

        st.radio("Choose the answer:", st.session_state.mc_options, key="mc_selected")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Submit"):
                if st.session_state.mc_selected is None:
                    st.warning("Pick an option first.")
                else:
                    if st.session_state.mc_selected == st.session_state.mc_answer:
                        st.success("✅ Correct!")
                        st.session_state.correct += 1
                    else:
                        st.error(f"✗ Not quite. Correct: {st.session_state.mc_answer}")
                    st.session_state.i += 1
                    st.session_state.mc_i = -1  # force new options next card
        with c2:
            if st.button("Skip"):
                st.session_state.i += 1
                st.session_state.mc_i = -1
