import streamlit as st
from supabase import create_client
import time
import random

# --- 1. Supabase 接続 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. ロジック & クラス ---
class Card:
    def __init__(self, name, ctype, power, condition_func, cond_text, desc):
        self.name, self.type, self.power, self.condition_func, self.cond_text, self.desc = name, ctype, power, condition_func, cond_text, desc

def check_pair(d): return any(d.count(x) >= 2 for x in set(d))
def check_three(d): return any(d.count(x) >= 3 for x in set(d))
def check_straight(d): 
    s = sorted(list(set(d)))
    return any(s[i:i+5] == list(range(s[i], s[i]+5)) for i in range(len(s)-4))
def check_full_house(d): 
    counts = [d.count(x) for x in set(d)]
    return 3 in counts and 2 in counts
def check_yahtzee(d): return len(set(d)) == 1

# カード定義
CARD_DB = {
    "ジェミニ・ダガー": Card("ジェミニ・ダガー", "attack", 15, check_pair, "ペア", "二連撃。"),
    "トライ・ブラスト": Card("トライ・ブラスト", "attack", 25, check_three, "スリーカード", "爆発。"),
    "慈悲 of 祝福": Card("慈悲 of 祝福", "heal", 35, check_pair, "ペア", "HP回復。"),
}
INNATE_DECK = [
    Card("固有:トリニティ", "attack", 20, check_three, "スリーカード", "固有の三連撃。"),
    Card("固有:五連光破斬", "attack", 30, check_straight, "ストレート", "五行の一撃。"),
    Card("固有:神罰の五連星", "attack", 50, check_yahtzee, "ヤッツィー", "究極の神罰。")
]

def get_data(): return supabase.table("game_state").select("*").eq("id", 1).execute().data[0]
def update_db(u): 
    try: supabase.table("game_state").update(u).eq("id", 1).execute()
    except Exception: pass

# --- 3. UI スタイル ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    div.stButton > button[key^="reroll"] { background-color: #FF4B4B !important; color: white !important; font-weight: bold !important; border-radius: 8px !important; }
    div.stButton > button[key^="draw"], div.stButton > button[key^="reset"] { background-color: #1E90FF !important; color: white !important; border-radius: 8px !important; }
    div.stButton > button[key^="atk_"] { background-color: #FFA500 !important; color: black !important; font-weight: bold !important; border-radius: 8px !important; }
    .dice-box { background: #1A1C23; padding: 15px; text-align: center; font-size: 35px; border-radius: 12px; border: 2px solid #444; color: #00FFFF; }
    .opp-dice-box { border-color: #FF4B4B; color: #FF4B4B; opacity: 0.7; font-size: 25px; }
</style>
""", unsafe_allow_html=True)

# --- 4. メインロジック ---
data = get_data()
role = st.sidebar.radio("役割を選択", ["Player 1", "Player 2"])
me, opp, my_id, opp_id = ("p1", "p2", 1, 2) if role == "Player 1" else ("p2", "p1", 2, 1)

st.title("⚔️ TACTICAL YAHTZEE LIVE")

# ステータス表示
c1, c2 = st.columns(2)
with c1:
    st.write(f"**YOU (P{my_id})**")
    st.markdown(f"## HP: {data[f'hp{my_id}']}")
    st.progress(min(1.0, max(0, data[f'hp{my_id}']) / 100))
with c2:
    st.write(f"**ENEMY (P{opp_id}) DICE**")
    st.markdown(f"## HP: {data[f'hp{opp_id}']}")
    st.progress(min(1.0, max(0, data[f'hp{opp_id}']) / 100))
    o_dice = data.get(f"{opp}_dice", [1,1,1,1,1])
    d_cols = st.columns(5)
    for i in range(5): d_cols[i].markdown(f"<div class='dice-box opp-dice-box'>{o_dice[i]}</div>", unsafe_allow_html=True)

st.divider()

if data["turn"] == (f"P{my_id}"):
    if st.session_state.get("last_t_count") != data["turn_count"]:
        st.session_state.dice = [random.randint(1, 6) for _ in range(5)]
        st.session_state.rolls_left = 2
        st.session_state.keep = [False] * 5
        st.session_state["last_t_count"] = data["turn_count"]
        update_db({f"{me}_dice": st.session_state.dice})
        st.rerun()

    st.write("🎲 あなたのダイス")
    my_d_cols = st.columns(5)
    for i in range(5):
        my_d_cols[i].markdown(f"<div class='dice-box'>{st.session_state.dice[i]}</div>", unsafe_allow_html=True)
        st.session_state.keep[i] = my_d_cols[i].checkbox("Keep", key=f"k{i}")

    used_innate = data.get(f"{me}_used_innate", [])
    if "hand" not in st.session_state: st.session_state.hand = []
    pool = [c for c in INNATE_DECK if c.name not in used_innate]
    for h in st.session_state.hand:
        if h in CARD_DB: pool.append(CARD_DB[h])
    
    available = [c for c in pool if c.condition_func(st.session_state.dice)]

    st.write("### ⚔️ アクション")
    for idx, card in enumerate(available):
        total_p = card.power + data.get(f"{me}_bonus", 0) if card.type == "attack" else card.power
        if st.button(f"【{card.cond_text}】{card.name} ({total_p})", key=f"atk_{idx}"):
            updates = {"turn": f"P{opp_id}", "turn_count": data["turn_count"]+1}
            if card.type == "attack": updates[f"hp{opp_id}"] = data[f"hp{opp_id}"] - total_p
            elif card.type == "heal": updates[f"hp{my_id}"] = data[f"hp{my_id}"] + total_p
            
            if "固有" in card.name:
                new_used = used_innate + [card.name]
                if len(new_used) >= 3:
                    updates[f"{me}_used_innate"] = []; updates[f"{me}_bonus"] = data.get(f"{me}_bonus", 0) + 10
                else: updates[f"{me}_used_innate"] = new_used
            else: st.session_state.hand.remove(card.name)
            update_db(updates); st.rerun()

    st.divider()
    col_x, col_y = st.columns(2)
    with col_x:
        if st.session_state.rolls_left > 0:
            if st.button(f"🎲 選択以外を振り直す (残り{st.session_state.rolls_left}回)", key="reroll_btn"):
                for i in range(5):
                    if not st.session_state.keep[i]: st.session_state.dice[i] = random.randint(1, 6)
                st.session_state.rolls_left -= 1
                update_db({f"{me}_dice": st.session_state.dice})
                st.rerun()
    with col_y:
        if st.button(f"🎴 確定してドロー・交代 (手札:{len(st.session_state.hand)}/5)", key="draw_btn"):
            deck = data["deck"]
            if deck and len(st.session_state.hand) < 5:
                st.session_state.hand.append(deck.pop())
                update_db({"deck": deck, "turn": f"P{opp_id}", "turn_count": data["turn_count"]+1})
            else: update_db({"turn": f"P{opp_id}", "turn_count": data["turn_count"]+1})
            st.rerun()
else:
    st.info("相手のターンです...")
    time.sleep(2)
    st.rerun()

if st.sidebar.button("🚨 全リセット", key="reset_all"):
    update_db({"hp1": 100, "hp2": 100, "turn": "P1", "turn_count": 0, "p1_used_innate": [], "p2_used_innate": [], "p1_bonus": 0, "p2_bonus": 0, "p1_dice": [1,1,1,1,1], "p2_dice": [1,1,1,1,1], "deck": ["ジェミニ・ダガー"]*10})
    st.session_state.hand = []; st.rerun()
