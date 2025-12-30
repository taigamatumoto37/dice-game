import streamlit as st
from supabase import create_client
import time
import random

# --- 1. Supabase 接続 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. 判定ロジック & カード定義 ---
class Card:
    def __init__(self, name, ctype, power, condition_func, cond_text, desc, effect_type=None, duration=0):
        self.name, self.type, self.power, self.condition_func, self.cond_text = name, ctype, power, condition_func, cond_text
        self.desc, self.effect_type, self.duration = desc, effect_type, duration

def check_pair(d): return any(d.count(x) >= 2 for x in set(d))
def check_three(d): return any(d.count(x) >= 3 for x in set(d))
def check_straight(d): 
    s = sorted(list(set(d)))
    return any(s[i:i+5] == list(range(s[i], s[i]+5)) for i in range(len(s)-4))
def check_full_house(d): 
    counts = [d.count(x) for x in set(d)]
    return 3 in counts and 2 in counts
def check_yahtzee(d): return len(set(d)) == 1

CARD_DB = {
    "ジェミニ・ダガー": Card("ジェミニ・ダガー", "attack", 15, check_pair, "ペア", "双子の短剣による二連撃。"),
    "トライ・ブラスト": Card("トライ・ブラスト", "attack", 25, check_three, "スリーカード", "三位一体の爆発。"),
    "慈悲 of 祝福": Card("慈悲 of 祝福", "heal", 35, check_pair, "ペア", "HP上限を超えて回復可能。"),
}
INNATE_DECK = [
    Card("固有:トリニティ", "attack", 20, check_three, "スリーカード", "固有の三連撃。"),
    Card("固有:五連光破斬", "attack", 30, check_straight, "ストレート", "五行の力。"),
    Card("固有:神罰の五連星", "attack", 50, check_yahtzee, "ヤッツィー", "究極の五連星。")
]

def get_data(): return supabase.table("game_state").select("*").eq("id", 1).execute().data[0]
def update_db(u): supabase.table("game_state").update(u).eq("id", 1).execute()

# --- 3. UIデザイン ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    .dice-container { display: flex; justify-content: space-around; margin-bottom: 20px; }
    .dice-box { background: #1A1C23; padding: 15px; text-align: center; font-size: 30px; border-radius: 10px; border: 2px solid #444; color: #00FFFF; width: 60px; height: 60px; line-height: 30px; }
    .opp-dice-box { border-color: #FF4B4B; color: #FF4B4B; opacity: 0.8; }
    .hp-text { font-size: 38px; font-weight: bold; color: #00FFAA; }
</style>
""", unsafe_allow_html=True)

# --- 4. メインロジック ---
data = get_data()

# 役割設定
role = st.sidebar.radio("役割を選択", ["Player 1", "Player 2"])
me, opp, my_id, opp_id = ("p1", "p2", 1, 2) if role == "Player 1" else ("p2", "p1", 2, 1)

# 全リセット
if st.sidebar.button("🚨 全リセット"):
    update_db({"hp1": 100, "hp2": 100, "turn": "P1", "turn_count": 0, "p1_status": None, "p2_status": None, "p1_used_innate": [], "p2_used_innate": [], "p1_bonus": 0, "p2_bonus": 0, "p1_dice": [1,1,1,1,1], "p2_dice": [1,1,1,1,1]})
    st.rerun()

st.title("⚔️ YAHTZEE TACTICS - LIVE")

# --- HP & 相手のダイス表示 ---
c1, c2 = st.columns(2)
with c1:
    st.write(f"**YOU (P{my_id})**")
    st.markdown(f"<p class='hp-text'>{data[f'hp{my_id}']}</p>", unsafe_allow_html=True)
    st.progress(min(1.0, max(0, data[f'hp{my_id}']) / 100))

with c2:
    st.write(f"**ENEMY (P{opp_id})**")
    st.markdown(f"<p class='hp-text'>{data[f'hp{opp_id}']}</p>", unsafe_allow_html=True)
    st.progress(min(1.0, max(0, data[f'hp{opp_id}']) / 100))
    # 相手のダイスをリアルタイム表示
    opp_dice = data.get(f"{opp}_dice", [1,1,1,1,1])
    cols = st.columns(5)
    for i in range(5):
        cols[i].markdown(f"<div class='dice-box opp-dice-box'>{opp_dice[i]}</div>", unsafe_allow_html=True)

st.divider()

# --- 自分のターン処理 ---
if data["turn"] == (f"P{my_id}"):
    # ターン開始初期化
    if st.session_state.get("last_t_count") != data["turn_count"]:
        new_dice = [random.randint(1, 6) for _ in range(5)]
        st.session_state.dice = new_dice
        st.session_state.rolls_left = 2
        st.session_state.keep = [False] * 5
        st.session_state["last_t_count"] = data["turn_count"]
        # 初期ダイスをDBへ
        update_db({f"{me}_dice": new_dice})
        st.rerun()

    st.write(f"🎲 あなたのダイス (残り振り直し: {st.session_state.rolls_left}回)")
    d_cols = st.columns(5)
    for i in range(5):
        with d_cols[i]:
            st.markdown(f"<div class='dice-box'>{st.session_state.dice[i]}</div>", unsafe_allow_html=True)
            st.session_state.keep[i] = st.checkbox("Keep", key=f"k{i}")

    # --- アクションエリア ---
    used_innate = data.get(f"{me}_used_innate", [])
    pool = [c for c in INNATE_DECK if c.name not in used_innate]
    if "hand" not in st.session_state: st.session_state.hand = []
    for h in st.session_state.hand:
        if h in CARD_DB: pool.append(CARD_DB[h])
    
    available = [c for c in pool if c.condition_func(st.session_state.dice)]

    if available:
        for idx, card in enumerate(available):
            if st.button(f"発動：{card.name}", key=f"btn_{idx}"):
                latest = get_data()
                bonus = latest.get(f"{me}_bonus", 0)
                updates = {"turn": f"P{opp_id}", "turn_count": latest["turn_count"]+1}
                if card.type == "attack": updates[f"hp{opp_id}"] = latest[f"hp{opp_id}"] - (card.power + bonus)
                elif card.type == "heal": updates[f"hp{my_id}"] = latest[f"hp{my_id}"] + card.power
                
                if "固有" in card.name:
                    new_used = used_innate + [card.name]
                    if len(new_used) >= 3:
                        updates[f"{me}_used_innate"] = []
                        updates[f"{me}_bonus"] = bonus + 10
                    else: updates[f"{me}_used_innate"] = new_used
                else: st.session_state.hand.remove(card.name)
                update_db(updates); st.rerun()

    # ダイス操作
    col_x, col_y = st.columns(2)
    with col_x:
        if st.session_state.rolls_left > 0 and st.button("🎲 振り直す"):
            for i in range(5):
                if not st.session_state.keep[i]: st.session_state.dice[i] = random.randint(1, 6)
            st.session_state.rolls_left -= 1
            update_db({f"{me}_dice": st.session_state.dice}) # DB同期
            st.rerun()
    with col_y:
        if len(st.session_state.hand) < 5 and st.button("🎴 ドロー交代"):
            deck = data["deck"]
            if deck:
                st.session_state.hand.append(deck.pop())
                update_db({"deck": deck, "turn": f"P{opp_id}", "turn_count": data["turn_count"]+1})
                st.rerun()

else:
    st.info("相手のターンを待機中...")
    time.sleep(2)
    st.rerun()
