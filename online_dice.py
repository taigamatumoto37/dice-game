import streamlit as st
from supabase import create_client
import time
import random

# --- 1. Supabase 接続 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. 判定ロジック (tttt.py) ---
def check_pair(d): return any(d.count(x) >= 2 for x in set(d))
def check_three(d): return any(d.count(x) >= 3 for x in set(d))
def check_straight(d): 
    s = sorted(list(set(d)))
    return any(s[i:i+5] == list(range(s[i], s[i]+5)) for i in range(len(s)-4))
def check_full_house(d): 
    counts = [d.count(x) for x in set(d)]
    return 3 in counts and 2 in counts
def check_yahtzee(d): return len(set(d)) == 1

class Card:
    def __init__(self, name, ctype, power, condition_func, cond_text, rarity, status_effect=None):
        self.name, self.type, self.power, self.condition_func, self.cond_text, self.rarity, self.status_effect = name, ctype, power, condition_func, cond_text, rarity, status_effect

# カードDB
CARD_DB = {
    "ジェミニ・ダガー": Card("ジェミニ・ダガー", "attack", 15, check_pair, "ペア", "弱"),
    "トライ・ブラスト": Card("トライ・ブラスト", "attack", 25, check_three, "スリーカード", "中"),
    "崩壊の紫煙(毒)": Card("崩壊の紫煙(毒)", "status", 0, check_three, "スリーカード", "中", ("poison", 3)),
    "天階の連撃": Card("天階の連撃", "attack", 40, check_straight, "ストレート", "強"),
    "煉獄の業火(炎)": Card("煉獄の業火(炎)", "status", 0, check_straight, "ストレート", "強", ("burn", 2)),
    "慈悲の祝福": Card("慈悲の祝福", "heal", 30, check_pair, "ペア", "レア"),
    "終焉 of 聖家": Card("終焉 of 聖家", "attack", 60, check_full_house, "フルハウス", "レア")
}

INNATE_CARDS = [
    Card("固有:トリニティ", "attack", 20, check_three, "スリーカード", "固有"),
    Card("固有:五連光破斬", "attack", 25, check_straight, "ストレート", "固有"),
    Card("固有:神罰の五連星", "attack", 50, check_yahtzee, "ヤッツィー", "固有")
]

# --- 3. データベース同期 ---
def get_data(): return supabase.table("game_state").select("*").eq("id", 1).execute().data[0]
def update_db(u): supabase.table("game_state").update(u).eq("id", 1).execute()
def create_deck():
    d = (["ジェミニ・ダガー"]*20 + ["トライ・ブラスト"]*16 + ["崩壊の紫煙(毒)"]*2 + ["天階の連撃"]*10 + ["煉獄の業火(炎)"]*2 + ["慈悲の祝福"]*5 + ["終焉 of 聖家"]*5)
    random.shuffle(d)
    return d

# --- 4. UIデザイン ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    div.stButton > button {
        background-color: #FF4B4B !important; color: white !important; border: none !important;
        border-radius: 10px !important; height: 3em !important; width: 100%; font-weight: bold !important;
    }
    .hp-text { font-size: 40px; font-weight: bold; color: #00FFAA; text-shadow: 0 0 10px #00FFAA; }
    .dice-box { background: #1A1C23; border: 2px solid #444; border-radius: 12px; padding: 15px; text-align: center; font-size: 45px; color: #00FFFF; text-shadow: 0 0 15px #00FFFF; }
    .card-row { background: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 6px solid #FF4B4B; margin: 10px 0; }
    .win-msg { font-size: 60px; color: #FFD700; text-align: center; font-weight: bold; text-shadow: 0 0 20px #FFD700; }
</style>
""", unsafe_allow_html=True)

# --- 5. メインロジック ---
data = get_data()

# ★終了判定
if data["hp1"] <= 0 or data["hp2"] <= 0:
    winner = "PLAYER 1" if data["hp2"] <= 0 else "PLAYER 2"
    st.markdown(f"<p class='win-msg'>🏆 {winner} WINNER!</p>", unsafe_allow_html=True)
    if st.button("♻️ ゲームを再起動"):
        update_db({"hp1": 150, "hp2": 150, "turn": "P1", "turn_count": 0, "p1_bonus": 0, "p2_bonus": 0, "deck": create_deck()})
        st.rerun()
    st.stop()

role = st.sidebar.radio("ROLE SELECT", ["Player 1", "Player 2"])
me, opp, my_turn_id = ("p1", "p2", "P1") if role == "Player 1" else ("p2", "p1", "P2")

st.markdown("# ⚔️ YAHTZEE TACTICS ⚔️")

# HP表示
c_p1, c_p2 = st.columns(2)
for i, p_id in enumerate(["p1", "p2"]):
    with (c_p1 if i == 0 else c_p2):
        st.markdown(f"### PLAYER {i+1}")
        hp = data[f"hp{i+1}"]
        st.markdown(f"<p class='hp-text'>{hp} / 150</p>", unsafe_allow_html=True)
        st.progress(max(0, hp) / 150)

st.divider()

if data["turn"] == my_turn_id:
    # ★毎ターン自動ダイス振り出し
    if st.session_state.get("last_turn") != data["turn_count"]:
        st.session_state.dice = [random.randint(1, 6) for _ in range(5)]
        st.session_state.phase = "action"
        st.session_state["last_turn"] = data["turn_count"]
        st.rerun()

    st.success("あなたのターンです (ダイスを振りました)")
    
    # ダイス表示
    st.write("### 🎲 今回の出目")
    d_cols = st.columns(5)
    for i in range(5):
        d_cols[i].markdown(f"<div class='dice-box'>{st.session_state.dice[i]}</div>", unsafe_allow_html=True)

    if st.session_state.phase == "action":
        c1, c2 = st.columns(2)
        if c1.button("🎴 ドローしてターン終了"):
            deck = data["deck"]
            if deck:
                if "hand" not in st.session_state: st.session_state.hand = []
                st.session_state.hand.append(deck.pop())
                update_db({"deck": deck, "turn": "P2" if my_turn_id=="P1" else "P1", "turn_count": data["turn_count"]+1})
                st.rerun()
        if c2.button("⚔️ 攻撃フェーズへ"):
            st.session_state.phase = "battle"
            st.rerun()

    elif st.session_state.phase == "battle":
        # 攻撃判定
        used = data.get(f"{me}_used_innate", [])
        pool = [c for c in INNATE_CARDS if c.name not in used]
        for h_name in st.session_state.get("hand", []):
            if h_name in CARD_DB: pool.append(CARD_DB[h_name])
        
        available = [c for c in pool if c.condition_func(st.session_state.dice)]

        if not available:
            st.warning("この出目では発動できる技がありません。")
            if st.button("パスして交代"):
                update_db({"turn": "P2" if my_turn_id=="P1" else "P1", "turn_count": data["turn_count"]+1})
                st.rerun()
        else:
            for idx, card in enumerate(available):
                st.markdown(f"<div class='card-row'><strong>{card.name}</strong> (条件: {card.cond_text})<br>威力: {card.power}</div>", unsafe_allow_html=True)
                if st.button(f"発動：{card.name}", key=f"btn_{idx}"):
                    latest = get_data()
                    bonus = latest.get(f"{me}_bonus", 0)
                    updates = {"turn": "P2" if my_turn_id=="P1" else "P1", "turn_count": latest["turn_count"]+1}
                    
                    if card.type == "attack":
                        target = "hp2" if me == "p1" else "hp1"
                        updates[target] = max(0, latest[target] - (card.power + bonus))
                    elif card.type == "heal":
                        updates[f"hp{1 if me=='p1' else 2}"] = min(150, latest[f"hp{1 if me=='p1' else 2}"] + card.power)

                    if "固有" not in card.name: st.session_state.hand.remove(card.name)
                    update_db(updates)
                    st.rerun()
else:
    st.info("相手のターンを待っています...")
    time.sleep(3)
    st.rerun()

st.sidebar.title("🎴 手札")
for h in st.session_state.get("hand", []): st.sidebar.info(h)
if st.sidebar.button("♻️ フルリセット"):
    update_db({"hp1": 150, "hp2": 150, "turn": "P1", "turn_count": 0, "p1_bonus": 0, "p2_bonus": 0, "deck": create_deck()})
    st.session_state.hand = []
    st.rerun()
