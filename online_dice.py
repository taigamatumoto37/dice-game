import streamlit as st
from supabase import create_client
import time
import random

# --- 1. Supabase 接続 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. 判定ロジック & カード定義 ---
def check_pair(d): return any(d.count(x) >= 2 for x in set(d))
def check_three(d): return any(d.count(x) >= 3 for x in set(d))
def check_straight(d): 
    s = sorted(list(set(d)))
    return any(s[i:i+5] == list(range(s[i], s[i]+5)) for i in range(len(s)-4))
def check_full_house(d): 
    counts = [d.count(x) for x in set(d)]
    return 3 in counts and 2 in counts

class Card:
    def __init__(self, name, ctype, power, condition_func, cond_text, effect_type=None, duration=0):
        self.name, self.type, self.power, self.condition_func, self.cond_text = name, ctype, power, condition_func, cond_text
        self.effect_type, self.duration = effect_type, duration

CARD_DB = {
    "ジェミニ・ダガー": Card("ジェミニ・ダガー", "attack", 15, check_pair, "ペア"),
    "トライ・ブラスト": Card("トライ・ブラスト", "attack", 25, check_three, "スリーカード"),
    "慈悲の祝福": Card("慈悲の祝福", "heal", 35, check_pair, "ペア"), # 上限なく回復可能
    "崩壊の紫煙": Card("崩壊の紫煙", "status", 5, check_three, "スリーカード", "poison", 3),
    "煉獄の業火": Card("煉獄の業火", "status", 10, check_straight, "ストレート", "burn", 2),
    "天階の連撃": Card("天階の連撃", "attack", 40, check_straight, "ストレート"),
    "終焉 of 聖家": Card("終焉 of 聖家", "attack", 60, check_full_house, "フルハウス")
}

def get_data(): return supabase.table("game_state").select("*").eq("id", 1).execute().data[0]
def update_db(u): supabase.table("game_state").update(u).eq("id", 1).execute()

# --- 3. UIデザイン (HP表示を強化) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    div.stButton > button { background-color: #FF4B4B !important; color: white !important; font-weight: bold !important; border-radius: 10px !important; border: none !important; }
    .hp-text { font-size: 38px; font-weight: bold; color: #00FFAA; text-shadow: 0 0 15px #00FFAA66; }
    .status-badge { padding: 4px 10px; border-radius: 6px; font-size: 13px; font-weight: bold; margin-top: 5px; display: inline-block; }
    .poison { background: #8A2BE2; } .burn { background: #FF4500; }
    .card-info { background: #1E1E26; padding: 12px; border-radius: 10px; border-left: 5px solid #FF4B4B; margin-bottom: 8px; }
    .heal-val { color: #00FFAA; font-weight: bold; font-size: 1.1em; }
</style>
""", unsafe_allow_html=True)

# --- 4. メインロジック ---
data = get_data()

# 終了判定
if data["hp1"] <= 0 or data["hp2"] <= 0:
    st.markdown(f"<h1 style='text-align:center;'>🏆 {'Player 1' if data['hp2'] <= 0 else 'Player 2'} WIN</h1>", unsafe_allow_html=True)
    if st.button("♻️ ゲームをフルリセット"):
        update_db({"hp1": 100, "hp2": 100, "turn": "P1", "turn_count": 0, "p1_status": None, "p2_status": None, "deck": (["ジェミニ・ダガー"]*20 + ["慈悲の祝福"]*10 + ["煉獄の業火"]*5)}) # 簡易デッキ
        st.rerun()
    st.stop()

role = st.sidebar.radio("役割", ["Player 1", "Player 2"])
me, opp, my_id, opp_id = ("p1", "p2", 1, 2) if role == "Player 1" else ("p2", "p1", 2, 1)

st.title("⚔️ UNLIMITED HP BATTLE")

# ステータス表示
c1, c2 = st.columns(2)
for i, p_prefix in enumerate(["p1", "p2"]):
    with (c1 if i == 0 else c2):
        st.write(f"**PLAYER {i+1}**")
        hp = data[f"hp{i+1}"]
        st.markdown(f"<p class='hp-text'>{hp}</p>", unsafe_allow_html=True)
        # バーは100を基準にしつつ、100を超えたら満タン表示
        st.progress(min(1.0, max(0, hp) / 100))
        s = data.get(f"{p_prefix}_status")
        if s: st.markdown(f"<span class='status-badge {s['type']}'>{s['type'].upper()} 残:{s['dur']}回</span>", unsafe_allow_html=True)

st.divider()

if data["turn"] == (f"P{my_id}"):
    # --- ターン開始時 (ダイス更新 & 持続ダメ) ---
    if st.session_state.get("last_t_count") != data["turn_count"]:
        updates = {"turn_count": data["turn_count"]}
        current_hp = data[f"hp{my_id}"]
        s = data.get(f"{me}_status")
        if s and s['dur'] > 0:
            current_hp -= s['pow']
            new_dur = s['dur'] - 1
            updates[f"{me}_status"] = {"type": s['type'], "pow": s['pow'], "dur": new_dur} if new_dur > 0 else None
            updates[f"hp{my_id}"] = current_hp
            update_db(updates)
            st.warning(f"状態異常ダメージ: {s['pow']}！")
            time.sleep(1); st.rerun()

        st.session_state.dice = [random.randint(1, 6) for _ in range(5)]
        st.session_state.rolls_left = 2
        st.session_state.keep = [False] * 5
        st.session_state["last_t_count"] = data["turn_count"]
        st.rerun()

    # ダイス
    st.write(f"🎲 振り直し可能: {st.session_state.rolls_left}回")
    d_cols = st.columns(5)
    for i in range(5):
        with d_cols[i]:
            st.markdown(f"<div style='background:#1A1C23; padding:15px; text-align:center; font-size:30px; border-radius:10px; border:1px solid #444; color:#00FFFF;'>{st.session_state.dice[i]}</div>", unsafe_allow_html=True)
            st.session_state.keep[i] = st.checkbox("Keep", key=f"k{i}")

    # 手札と技
    hand = st.session_state.get("hand", [])
    pool = [CARD_DB[h] for h in hand if h in CARD_DB]
    available = [c for c in pool if c.condition_func(st.session_state.dice)]

    st.write("### ⚔️ フェーズ：攻撃・行動")
    if available:
        for idx, card in enumerate(available):
            val_text = f"<span class='heal-val'>OVER HEAL: +{card.power}</span>" if card.type == "heal" else f"威力: {card.power}"
            st.markdown(f"<div class='card-info'><strong>{card.name}</strong> ({card.cond_text}) | {val_text}</div>", unsafe_allow_html=True)
            if st.button(f"発動：{card.name}", key=f"btn_{idx}"):
                latest = get_data()
                updates = {"turn": f"P{opp_id}", "turn_count": latest["turn_count"] + 1}
                if card.type == "attack": updates[f"hp{opp_id}"] = latest[f"hp{opp_id}"] - card.power
                elif card.type == "heal": updates[f"hp{my_id}"] = latest[f"hp{my_id}"] + card.power # ここに上限(min)をつけない
                elif card.type == "status": updates[f"{opp}_status"] = {"type": card.effect_type, "pow": card.power, "dur": card.duration}
                
                hand.remove(card.name); st.session_state.hand = hand
                update_db(updates); st.rerun()

    # 共通アクション
    col_x, col_y = st.columns(2)
    with col_x:
        if st.session_state.rolls_left > 0 and st.button("🎲 振り直す"):
            for i in range(5):
                if not st.session_state.keep[i]: st.session_state.dice[i] = random.randint(1, 6)
            st.session_state.rolls_left -= 1; st.rerun()
    with col_y:
        if len(hand) < 5 and st.button("🎴 ドローして交代"):
            deck = data["deck"]
            if deck:
                hand.append(deck.pop()); st.session_state.hand = hand
                update_db({"deck": deck, "turn": f"P{opp_id}", "turn_count": data["turn_count"]+1})
                st.rerun()
else:
    st.info("相手のターンです...")
    time.sleep(3); st.rerun()
