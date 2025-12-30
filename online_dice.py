import streamlit as st
from supabase import create_client
import time
import random

# --- 1. Supabase 接続 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. 判定ロジック & カードDB ---
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
    def __init__(self, name, ctype, power, condition_func, cond_text, rarity):
        self.name, self.type, self.power, self.condition_func, self.cond_text, self.rarity = name, ctype, power, condition_func, cond_text, rarity

CARD_DB = {
    "ジェミニ・ダガー": Card("ジェミニ・ダガー", "attack", 15, check_pair, "ペア", "弱"),
    "トライ・ブラスト": Card("トライ・ブラスト", "attack", 25, check_three, "スリーカード", "中"),
    "天階の連撃": Card("天階の連撃", "attack", 40, check_straight, "ストレート", "強"),
    "慈悲の祝福": Card("慈悲の祝福", "heal", 20, check_pair, "ペア", "レア"),
    "終焉 of 聖家": Card("終焉 of 聖家", "attack", 50, check_full_house, "フルハウス", "レア")
}
INNATE_CARDS = [
    Card("固有:トリニティ", "attack", 15, check_three, "スリーカード", "固有"),
    Card("固有:五連光破斬", "attack", 20, check_straight, "ストレート", "固有"),
    Card("固有:神罰の五連星", "attack", 40, check_yahtzee, "ヤッツィー", "固有")
]

def get_data(): return supabase.table("game_state").select("*").eq("id", 1).execute().data[0]
def update_db(u): supabase.table("game_state").update(u).eq("id", 1).execute()

# --- 3. UIデザイン ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    div.stButton > button { background-color: #FF4B4B !important; color: white !important; font-weight: bold !important; border-radius: 10px !important; width: 100%; border: none !important;}
    .hp-text { font-size: 35px; font-weight: bold; color: #00FFAA; }
    .dice-box { background: #1A1C23; border: 2px solid #444; border-radius: 12px; padding: 10px; text-align: center; font-size: 40px; color: #00FFFF; box-shadow: 0 0 10px #00FFFF33; }
    .card-discard { background: #2D1414; border: 1px dashed #FF4B4B; padding: 10px; border-radius: 5px; margin-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 4. メインロジック ---
data = get_data()

# 終了判定 (HP 0以下)
if data["hp1"] <= 0 or data["hp2"] <= 0:
    winner = "Player 1" if data["hp2"] <= 0 else "Player 2"
    st.title(f"🏆 {winner} の勝利！")
    if st.button("♻️ ゲームを最初からやり直す"):
        update_db({"hp1": 100, "hp2": 100, "turn": "P1", "turn_count": 0, "p1_bonus": 0, "p2_bonus": 0})
        st.rerun()
    st.stop()

role = st.sidebar.radio("役割を選択", ["Player 1", "Player 2"])
me, opp, my_turn_id = ("p1", "p2", "P1") if role == "Player 1" else ("p2", "p1", "P2")

st.title("⚔️ YAHTZEE TACTICS (HP 100)")

# HP表示 (100基準)
c1, c2 = st.columns(2)
for i, p in enumerate(["p1", "p2"]):
    with (c1 if i == 0 else c2):
        st.write(f"PLAYER {i+1}")
        hp_val = data[f"hp{i+1}"]
        st.markdown(f"<p class='hp-text'>{hp_val} / 100</p>", unsafe_allow_html=True)
        st.progress(max(0, hp_val) / 100)

st.divider()

if data["turn"] == my_turn_id:
    # ターン開始時のダイス振り出し
    if st.session_state.get("last_t_count") != data["turn_count"]:
        st.session_state.dice = [random.randint(1, 6) for _ in range(5)]
        st.session_state.rolls_left = 2
        st.session_state.keep = [False] * 5
        st.session_state["last_t_count"] = data["turn_count"]
        st.rerun()

    st.write(f"🎲 残り振り直し: **{st.session_state.rolls_left}** 回")
    
    # ダイス表示とキープ
    d_cols = st.columns(5)
    for i in range(5):
        with d_cols[i]:
            st.markdown(f"<div class='dice-box'>{st.session_state.dice[i]}</div>", unsafe_allow_html=True)
            st.session_state.keep[i] = st.checkbox("Keep", key=f"k{i}", value=st.session_state.keep[i])

    # アクション
    col_a, col_b = st.columns(2)
    with col_a:
        if st.session_state.rolls_left > 0:
            if st.button("🎲 選択以外を振り直す"):
                for i in range(5):
                    if not st.session_state.keep[i]:
                        st.session_state.dice[i] = random.randint(1, 6)
                st.session_state.rolls_left -= 1
                st.rerun()
    
    with col_b:
        hand = st.session_state.get("hand", [])
        if len(hand) < 5:
            if st.button("🎴 確定してドロー交代"):
                deck = data["deck"]
                if deck:
                    hand.append(deck.pop())
                    st.session_state.hand = hand
                    update_db({"deck": deck, "turn": "P2" if my_turn_id=="P1" else "P1", "turn_count": data["turn_count"]+1})
                    st.rerun()
        else:
            st.error("手札が一杯です！下の廃棄エリアを使ってください。")

    # 攻撃
    st.divider()
    used = data.get(f"{me}_used_innate", [])
    pool = [c for c in INNATE_CARDS if c.name not in used]
    for h in hand:
        if h in CARD_DB: pool.append(CARD_DB[h])
    
    available = [c for c in pool if c.condition_func(st.session_state.dice)]

    if available:
        st.write("### ⚔️ 発動可能な技")
        for idx, card in enumerate(available):
            if st.button(f"発動：{card.name} ({card.cond_text})", key=f"atk_{idx}"):
                latest = get_data()
                updates = {"turn": "P2" if my_turn_id=="P1" else "P1", "turn_count": latest["turn_count"]+1}
                if card.type == "attack":
                    target = "hp2" if me == "p1" else "hp1"
                    updates[target] = max(0, latest[target] - card.power)
                elif card.type == "heal":
                    updates[f"hp{1 if me=='p1' else 2}"] = min(100, latest[f"hp{1 if me=='p1' else 2}"] + card.power)
                
                if "固有" not in card.name: hand.remove(card.name)
                st.session_state.hand = hand
                update_db(updates)
                st.rerun()

    # 廃棄交代 (手札5枚時)
    if len(hand) >= 5:
        st.write("### 🗑️ カードを1枚捨てて交代")
        for idx, h_card in enumerate(hand):
            c_col1, c_col2 = st.columns([3, 1])
            c_col1.markdown(f"<div class='card-discard'>{h_card}</div>", unsafe_allow_html=True)
            if c_col2.button("捨てる", key=f"disc_{idx}"):
                hand.pop(idx)
                deck = data["deck"]
                if deck: hand.append(deck.pop())
                st.session_state.hand = hand
                update_db({"deck": deck, "turn": "P2" if my_turn_id=="P1" else "P1", "turn_count": data["turn_count"]+1})
                st.rerun()

else:
    st.info("相手が戦略を練っています...")
    time.sleep(3)
    st.rerun()

st.sidebar.write("### 手札")
for h in st.session_state.get("hand", []): st.sidebar.info(h)
if st.sidebar.button("♻️ フルリセット"):
    update_db({"hp1": 100, "hp2": 100, "turn": "P1", "turn_count": 0, "p1_bonus": 0, "p2_bonus": 0})
    st.session_state.hand = []
    st.rerun()
