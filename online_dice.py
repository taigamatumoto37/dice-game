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
    "トライ・ブラスト": Card("トライ・ブラスト", "attack", 25, check_three, "スリーカード", "三位一体の魔力による爆発。"),
    "慈悲の祝福": Card("慈悲の祝福", "heal", 35, check_pair, "ペア", "聖なる光が負傷を癒やす。"),
    "崩壊の紫煙": Card("崩壊の紫煙", "status", 5, check_three, "スリーカード", "3ターンの間、毒で毎ターン5ダメージ。", "poison", 3)
}

# 固有カードの定義
INNATE_DECK = [
    Card("固有:トリニティ", "attack", 20, check_three, "スリーカード", "固有の魔力による三連撃。"),
    Card("固有:五連光破斬", "attack", 30, check_straight, "ストレート", "五行の力を乗せた一撃。"),
    Card("固有:神罰の五連星", "attack", 50, check_yahtzee, "ヤッツィー", "神の裁きを下す究極の五連星。")
]

def get_data(): return supabase.table("game_state").select("*").eq("id", 1).execute().data[0]
def update_db(u): supabase.table("game_state").update(u).eq("id", 1).execute()

# --- 3. UIデザイン ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    div.stButton > button { background-color: #FF4B4B !important; color: white !important; font-weight: bold !important; border-radius: 10px !important; }
    .hp-text { font-size: 38px; font-weight: bold; color: #00FFAA; }
    .card-panel { background: #1E1E26; padding: 15px; border-radius: 12px; border-left: 5px solid #FF4B4B; margin-bottom: 10px; }
    .innate-panel { border-left: 5px solid #FFD700; background: #262214; }
    .bonus-msg { color: #FFD700; font-weight: bold; border: 1px solid #FFD700; padding: 5px; border-radius: 5px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- 4. メインロジック ---
data = get_data()

# 終了判定
if data["hp1"] <= 0 or data["hp2"] <= 0:
    st.title("🏆 Battle Finished")
    if st.button("♻️ ゲームをリセットして最初から"):
        update_db({"hp1": 100, "hp2": 100, "turn": "P1", "turn_count": 0, "p1_status": None, "p2_status": None, "p1_used_innate": [], "p2_used_innate": [], "p1_bonus": 0, "p2_bonus": 0})
        st.rerun()
    st.stop()

role = st.sidebar.radio("役割", ["Player 1", "Player 2"])
me, opp, my_id, opp_id = ("p1", "p2", 1, 2) if role == "Player 1" else ("p2", "p1", 2, 1)

st.title("⚔️ YAHTZEE TACTICS")

# --- サイドバー：リセット & 手札 ---
if st.sidebar.button("🚨 全リセット(緊急用)"):
    update_db({"hp1": 100, "hp2": 100, "turn": "P1", "turn_count": 0, "p1_status": None, "p2_status": None, "p1_used_innate": [], "p2_used_innate": [], "p1_bonus": 0, "p2_bonus": 0})
    st.session_state.clear()
    st.rerun()

st.sidebar.divider()
st.sidebar.write("### あなたの手札")
if "hand" not in st.session_state: st.session_state.hand = []
for h in st.session_state.hand: st.sidebar.info(h)

# HP & 状態
c1, c2 = st.columns(2)
for i, p_pre in enumerate(["p1", "p2"]):
    with (c1 if i == 0 else c2):
        st.write(f"**PLAYER {i+1}**")
        hp = data[f"hp{i+1}"]
        st.markdown(f"<p class='hp-text'>{hp}</p>", unsafe_allow_html=True)
        bonus = data.get(f"{p_pre}_bonus", 0)
        if bonus > 0: st.markdown(f"<div class='bonus-msg'>攻撃力 +{bonus} 覚醒中</div>", unsafe_allow_html=True)
        st.progress(min(1.0, max(0, hp) / 100))

st.divider()

if data["turn"] == (f"P{my_id}"):
    # ターン開始
    if st.session_state.get("last_t_count") != data["turn_count"]:
        updates = {"turn_count": data["turn_count"]}
        # 持続ダメージ処理
        s = data.get(f"{me}_status")
        if s and s['dur'] > 0:
            updates[f"hp{my_id}"] = data[f"hp{my_id}"] - s['pow']
            updates[f"{me}_status"] = {"type": s['type'], "pow": s['pow'], "dur": s['dur']-1} if s['dur']-1 > 0 else None
            update_db(updates); st.rerun()

        st.session_state.dice = [random.randint(1, 6) for _ in range(5)]
        st.session_state.rolls_left = 2
        st.session_state.keep = [False] * 5
        st.session_state["last_t_count"] = data["turn_count"]
        st.rerun()

    # ダイスエリア
    st.write(f"🎲 振り直し可能: {st.session_state.rolls_left}回")
    d_cols = st.columns(5)
    for i in range(5):
        with d_cols[i]:
            st.markdown(f"<div style='background:#1A1C23; padding:15px; text-align:center; font-size:30px; border-radius:10px; border:1px solid #444; color:#00FFFF;'>{st.session_state.dice[i]}</div>", unsafe_allow_html=True)
            st.session_state.keep[i] = st.checkbox("Keep", key=f"k{i}")

    # 技のプール構築
    used_innate = data.get(f"{me}_used_innate", [])
    # 固有カードを「未使用」のものだけ追加
    pool = [c for c in INNATE_DECK if c.name not in used_innate]
    # 手札カードを追加
    for h in st.session_state.hand:
        if h in CARD_DB: pool.append(CARD_DB[h])
    
    available = [c for c in pool if c.condition_func(st.session_state.dice)]

    st.write("### ⚔️ 行動を選択")
    if available:
        for idx, card in enumerate(available):
            is_innate = "固有" in card.name
            bonus_dmg = data.get(f"{me}_bonus", 0) if card.type == "attack" else 0
            
            st.markdown(f"""
                <div class='card-panel {"innate-panel" if is_innate else ""}'>
                    <strong>{card.name}</strong> | {'威力:' + str(card.power + bonus_dmg) if card.type=='attack' else card.type}<br>
                    <small>{card.desc}</small>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"発動：{card.name}", key=f"btn_{idx}"):
                latest = get_data()
                updates = {"turn": f"P{opp_id}", "turn_count": latest["turn_count"]+1}
                
                # 効果処理
                if card.type == "attack": 
                    updates[f"hp{opp_id}"] = latest[f"hp{opp_id}"] - (card.power + bonus_dmg)
                elif card.type == "heal": 
                    updates[f"hp{my_id}"] = latest[f"hp{my_id}"] + card.power
                elif card.type == "status":
                    updates[f"{opp}_status"] = {"type": card.effect_type, "pow": card.power, "dur": card.duration}

                # 固有カード使用記録
                if is_innate:
                    new_used = used_innate + [card.name]
                    # 全て使い切ったかチェック
                    if len(new_used) >= len(INNATE_DECK):
                        st.balloons()
                        updates[f"{me}_used_innate"] = [] # 復活
                        updates[f"{me}_bonus"] = latest.get(f"{me}_bonus", 0) + 10 # 攻撃ボーナス追加
                    else:
                        updates[f"{me}_used_innate"] = new_used
                else:
                    st.session_state.hand.remove(card.name)
                
                update_db(updates); st.rerun()

    # アクション
    st.divider()
    cx, cy = st.columns(2)
    with cx:
        if st.session_state.rolls_left > 0 and st.button("🎲 選択以外を振り直す"):
            for i in range(5):
                if not st.session_state.keep[i]: st.session_state.dice[i] = random.randint(1, 6)
            st.session_state.rolls_left -= 1; st.rerun()
    with cy:
        if len(st.session_state.hand) < 5 and st.button("🎴 交代してドロー"):
            deck = data["deck"]
            if deck:
                st.session_state.hand.append(deck.pop())
                update_db({"deck": deck, "turn": f"P{opp_id}", "turn_count": data["turn_count"]+1})
                st.rerun()
else:
    st.info("相手がダイスを振っています...")
    time.sleep(3); st.rerun()
