import streamlit as st
from supabase import create_client
import time
import random

# --- 1. Supabase 接続 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. 判定ロジック & 拡張カードデータ ---
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
        self.effect_type = effect_type # "poison" (毒), "burn" (炎)
        self.duration = duration     # 持続ターン数

CARD_DB = {
    "ジェミニ・ダガー": Card("ジェミニ・ダガー", "attack", 15, check_pair, "ペア"),
    "トライ・ブラスト": Card("トライ・ブラスト", "attack", 25, check_three, "スリーカード"),
    "慈悲の祝福": Card("慈悲の祝福", "heal", 30, check_pair, "ペア"),
    "崩壊の紫煙": Card("崩壊の紫煙", "status", 5, check_three, "スリーカード", "poison", 3), # 5ダメ×3ターン
    "煉獄の業火": Card("煉獄の業火", "status", 10, check_straight, "ストレート", "burn", 2), # 10ダメ×2ターン
    "天階の連撃": Card("天階の連撃", "attack", 40, check_straight, "ストレート"),
    "終焉 of 聖家": Card("終焉 of 聖家", "attack", 55, check_full_house, "フルハウス")
}

def get_data(): return supabase.table("game_state").select("*").eq("id", 1).execute().data[0]
def update_db(u): supabase.table("game_state").update(u).eq("id", 1).execute()

# --- 3. UIデザイン (ステータス表示を強化) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    div.stButton > button { background-color: #FF4B4B !important; color: white !important; font-weight: bold !important; border-radius: 10px !important; }
    .hp-text { font-size: 30px; font-weight: bold; color: #00FFAA; }
    .status-badge { padding: 2px 8px; border-radius: 5px; font-size: 14px; font-weight: bold; }
    .poison { background: #8A2BE2; color: white; } /* 紫: 毒 */
    .burn { background: #FF4500; color: white; }   /* 赤: 炎 */
    .card-info { background: #262730; padding: 12px; border-radius: 10px; border-left: 5px solid #FF4B4B; margin-bottom: 5px; }
    .damage-val { color: #FF4B4B; font-weight: bold; }
    .heal-val { color: #00FFAA; font-weight: bold; }
    .status-val { color: #DA70D6; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 4. メインロジック ---
data = get_data()

# ゲーム終了判定
if data["hp1"] <= 0 or data["hp2"] <= 0:
    st.title("🏆 Battle Result")
    st.write(f"勝者: {'Player 1' if data['hp2'] <= 0 else 'Player 2'}")
    if st.button("リセットして再戦"):
        update_db({"hp1": 100, "hp2": 100, "turn": "P1", "turn_count": 0, "p1_status": None, "p2_status": None})
        st.rerun()
    st.stop()

role = st.sidebar.radio("役割", ["Player 1", "Player 2"])
me, opp, my_id, opp_id = ("p1", "p2", 1, 2) if role == "Player 1" else ("p2", "p1", 2, 1)

st.title("⚔️ YAHTZEE TACTICS")

# ステータス表示エリア
c1, c2 = st.columns(2)
for i, p_prefix in enumerate(["p1", "p2"]):
    with (c1 if i == 0 else c2):
        st.write(f"PLAYER {i+1}")
        hp = data[f"hp{i+1}"]
        st.markdown(f"<p class='hp-text'>{hp} / 100</p>", unsafe_allow_html=True)
        # 状態異常の表示
        s = data.get(f"{p_prefix}_status")
        if s:
            st.markdown(f"<span class='status-badge {s['type']}'>{s['type'].upper()} (あと{s['dur']}回)</span>", unsafe_allow_html=True)
        st.progress(max(0, hp) / 100)

st.divider()

if data["turn"] == (f"P{my_id}"):
    # --- ターン開始時処理 (ダイス & 持続ダメージ) ---
    if st.session_state.get("last_t_count") != data["turn_count"]:
        current_hp = data[f"hp{my_id}"]
        updates = {"turn_count": data["turn_count"]} # 更新用辞書
        
        # 持続ダメージ判定
        s = data.get(f"{me}_status")
        if s and s['dur'] > 0:
            current_hp -= s['pow']
            st.warning(f"{s['type']}により {s['pow']} ダメージ！")
            new_dur = s['dur'] - 1
            updates[f"{me}_status"] = {"type": s['type'], "pow": s['pow'], "dur": new_dur} if new_dur > 0 else None
            updates[f"hp{my_id}"] = max(0, current_hp)
            update_db(updates)
            time.sleep(1)
            st.rerun()

        st.session_state.dice = [random.randint(1, 6) for _ in range(5)]
        st.session_state.rolls_left = 2
        st.session_state.keep = [False] * 5
        st.session_state["last_t_count"] = data["turn_count"]
        st.rerun()

    # --- ダイス操作エリア ---
    st.write(f"🎲 残り振り直し: {st.session_state.rolls_left}回")
    d_cols = st.columns(5)
    for i in range(5):
        with d_cols[i]:
            st.markdown(f"<div style='background:#1A1C23; border-radius:10px; padding:15px; text-align:center; font-size:30px; color:#00FFFF; border:1px solid #444;'>{st.session_state.dice[i]}</div>", unsafe_allow_html=True)
            st.session_state.keep[i] = st.checkbox("Keep", key=f"k{i}")

    # --- アクションエリア ---
    hand = st.session_state.get("hand", [])
    pool = []
    for h in hand:
        if h in CARD_DB: pool.append(CARD_DB[h])
    
    available = [c for c in pool if c.condition_func(st.session_state.dice)]

    st.write("### ⚔️ 技の発動 / 交代")
    if available:
        for idx, card in enumerate(available):
            if card.type == "attack": val = f"<span class='damage-val'>{card.power} DMG</span>"
            elif card.type == "heal": val = f"<span class='heal-val'>+{card.power} HP</span>"
            else: val = f"<span class='status-val'>{card.effect_type} {card.power}×{card.duration}T</span>"
            
            st.markdown(f"<div class='card-info'><strong>{card.name}</strong> ({card.cond_text}) | {val}</div>", unsafe_allow_html=True)
            if st.button(f"発動：{card.name}", key=f"atk_{idx}"):
                latest = get_data()
                updates = {"turn": f"P{opp_id}", "turn_count": latest["turn_count"] + 1}
                
                if card.type == "attack":
                    updates[f"hp{opp_id}"] = max(0, latest[f"hp{opp_id}"] - card.power)
                elif card.type == "heal":
                    updates[f"hp{my_id}"] = min(100, latest[f"hp{my_id}"] + card.power)
                elif card.type == "status":
                    updates[f"{opp}_status"] = {"type": card.effect_type, "pow": card.power, "dur": card.duration}
                
                hand.remove(card.name); st.session_state.hand = hand
                update_db(updates); st.rerun()

    # 共通ボタン
    col_x, col_y = st.columns(2)
    with col_x:
        if st.session_state.rolls_left > 0 and st.button("🎲 振り直す"):
            for i in range(5):
                if not st.session_state.keep[i]: st.session_state.dice[i] = random.randint(1, 6)
            st.session_state.rolls_left -= 1; st.rerun()
    with col_y:
        if len(hand) < 5 and st.button("🎴 ドロー交代"):
            deck = data["deck"]
            if deck:
                hand.append(deck.pop()); st.session_state.hand = hand
                update_db({"deck": deck, "turn": f"P{opp_id}", "turn_count": data["turn_count"]+1})
                st.rerun()

else:
    st.info("相手のターンです...")
    time.sleep(3); st.rerun()

st.sidebar.write("### あなたの手札")
for h in st.session_state.get("hand", []): st.sidebar.info(h)
