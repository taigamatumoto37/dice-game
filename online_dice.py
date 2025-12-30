import streamlit as st
from supabase import create_client
import time
import random

# --- 1. Supabase 接続 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. カード定義 & 判定ロジック ---
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

# 通常カードDB
CARD_DB = {
    "ジェミニ・ダガー": Card("ジェミニ・ダガー", "attack", 15, check_pair, "ペア", "双子の短剣による素早い二連撃。"),
    "トライ・ブラスト": Card("トライ・ブラスト", "attack", 25, check_three, "スリーカード", "三位一体の爆発。"),
    "慈悲 of 祝福": Card("慈悲 of 祝福", "heal", 35, check_pair, "ペア", "HP上限を超えて回復可能。"),
}
# 固有カードの定義 (マスターリスト)
INNATE_DECK = [
    Card("固有:トリニティ", "attack", 20, check_three, "スリーカード", "固有の魔力による三連撃。"),
    Card("固有:五連光破斬", "attack", 30, check_straight, "ストレート", "五行の力を乗せた一撃。"),
    Card("固有:神罰の五連星", "attack", 50, check_yahtzee, "ヤッツィー", "究極の神罰を下す。")
]

def get_data(): return supabase.table("game_state").select("*").eq("id", 1).execute().data[0]
def update_db(u): supabase.table("game_state").update(u).eq("id", 1).execute()

# --- 3. UIデザイン (ボタンの色分け設定) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    /* 青色ボタン (振り直し・リセット) */
    div.stButton > button[key^="reroll"], div.stButton > button[key^="reset"] {
        background-color: #1E90FF !important; color: white !important; font-weight: bold !important; border-radius: 8px !important;
    }
    /* 赤色ボタン (ドロー・交代) */
    div.stButton > button[key^="draw"] {
        background-color: #FF4B4B !important; color: white !important; font-weight: bold !important; border-radius: 8px !important;
    }
    /* オレンジ/金ボタン (攻撃カード発動) */
    div.stButton > button[key^="atk_"] {
        background-color: #FFA500 !important; color: black !important; font-weight: 1000 !important; border-radius: 8px !important; border: 2px solid white !important;
    }
    .dice-box { background: #1A1C23; padding: 15px; text-align: center; font-size: 35px; border-radius: 12px; border: 2px solid #444; color: #00FFFF; }
    .card-panel { background: #1E1E26; padding: 12px; border-radius: 10px; margin-bottom: 5px; border-left: 5px solid #FFA500; }
    .bonus-badge { color: #FFD700; font-weight: bold; border: 1px solid #FFD700; padding: 4px; border-radius: 5px; text-align: center; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 4. メインロジック ---
data = get_data()
role = st.sidebar.radio("役割を選択", ["Player 1", "Player 2"])
me, opp, my_id, opp_id = ("p1", "p2", 1, 2) if role == "Player 1" else ("p2", "p1", 2, 1)

st.title("⚔️ TACTICAL YAHTZEE")

# サイドバーのリセット
if st.sidebar.button("🚨 全リセット(青)", key="reset_all"):
    update_db({"hp1": 100, "hp2": 100, "turn": "P1", "turn_count": 0, "p1_used_innate": [], "p2_used_innate": [], "p1_bonus": 0, "p2_bonus": 0})
    st.session_state.hand = []
    st.rerun()

# HP表示
c1, c2 = st.columns(2)
for i, p_pre in enumerate(["p1", "p2"]):
    with (c1 if i == 0 else c2):
        st.write(f"**PLAYER {i+1}**")
        hp = data[f"hp{i+1}"]
        st.markdown(f"## {hp}")
        st.progress(min(1.0, max(0, hp) / 100))
        bonus = data.get(f"{p_pre}_bonus", 0)
        if bonus > 0: st.markdown(f"<div class='bonus-badge'>ATK +{bonus} 覚醒</div>", unsafe_allow_html=True)

st.divider()

if data["turn"] == (f"P{my_id}"):
    # ターン開始
    if st.session_state.get("last_t_count") != data["turn_count"]:
        st.session_state.dice = [random.randint(1, 6) for _ in range(5)]
        st.session_state.rolls_left = 2
        st.session_state.keep = [False] * 5
        st.session_state["last_t_count"] = data["turn_count"]
        st.rerun()

    # ダイスエリア
    st.write(f"🎲 残り振り直し: {st.session_state.rolls_left}回")
    d_cols = st.columns(5)
    for i in range(5):
        d_cols[i].markdown(f"<div class='dice-box'>{st.session_state.dice[i]}</div>", unsafe_allow_html=True)
        st.session_state.keep[i] = d_cols[i].checkbox("Keep", key=f"k{i}")

    # --- 技の構築 (固有カード + 手札) ---
    used_innate = data.get(f"{me}_used_innate", [])
    hand = st.session_state.get("hand", [])
    atk_bonus = data.get(f"{me}_bonus", 0)
    
    # 未使用の固有カードをプールに追加
    pool = [c for c in INNATE_DECK if c.name not in used_innate]
    # 手札のカードをプールに追加
    for h in hand:
        if h in CARD_DB: pool.append(CARD_DB[h])
    
    available = [c for c in pool if c.condition_func(st.session_state.dice)]

    st.write("### ⚔️ 発動可能なアクション")
    if available:
        for idx, card in enumerate(available):
            is_innate = "固有" in card.name
            total_dmg = card.power + (atk_bonus if card.type == "attack" else 0)
            effect_val = f"ダメージ: {total_dmg}" if card.type == "attack" else f"回復: {card.power}"
            
            st.markdown(f"<div class='card-panel'><strong>{card.name}</strong><br><small>{card.desc}</small></div>", unsafe_allow_html=True)
            
            # ボタンに条件と数値を記載 (オレンジ色)
            btn_label = f"【{card.cond_text}】で発動！ ({effect_val})"
            if st.button(btn_label, key=f"atk_{idx}"):
                latest = get_data()
                updates = {"turn": f"P{opp_id}", "turn_count": latest["turn_count"]+1}
                
                # ダメージ/回復処理
                if card.type == "attack":
                    updates[f"hp{opp_id}"] = latest[f"hp{opp_id}"] - total_dmg
                elif card.type == "heal":
                    updates[f"hp{my_id}"] = latest[f"hp{my_id}"] + total_dmg
                
                # 固有カードの復活・覚醒処理
                if is_innate:
                    new_used = used_innate + [card.name]
                    if len(new_used) >= len(INNATE_DECK):
                        st.balloons()
                        updates[f"{me}_used_innate"] = [] # 全復活
                        updates[f"{me}_bonus"] = atk_bonus + 10 # 覚醒
                    else:
                        updates[f"{me}_used_innate"] = new_used
                else:
                    hand.remove(card.name)
                    st.session_state.hand = hand
                
                update_db(updates); st.rerun()
    else:
        st.info("条件を満たすカードがありません。")

    st.divider()
    # 操作ボタン
    col_x, col_y = st.columns(2)
    with col_x:
        if st.session_state.rolls_left > 0:
            if st.button(f"🎲 振り直す (残{st.session_state.rolls_left})", key="reroll_btn"):
                for i in range(5):
                    if not st.session_state.keep[i]: st.session_state.dice[i] = random.randint(1, 6)
                st.session_state.rolls_left -= 1
                st.rerun()
    with col_y:
        if len(hand) < 5:
            if st.button(f"🎴 確定ドロー交代 (手札:{len(hand)}/5)", key="draw_btn"):
                latest_data = get_data()
                deck = latest_data["deck"]
                if deck:
                    hand.append(deck.pop())
                    st.session_state.hand = hand
                    update_db({"deck": deck, "turn": f"P{opp_id}", "turn_count": latest_data["turn_count"]+1})
                    st.rerun()
else:
    st.info("相手のターンです...")
    time.sleep(3)
    st.rerun()
