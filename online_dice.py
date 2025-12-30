import streamlit as st
from supabase import create_client
import time
import random

# --- 1. Supabase 接続 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. カード・役判定定義 ---
class Card:
    def __init__(self, name, ctype, power, condition_func, cond_text):
        self.name, self.type, self.power, self.condition_func, self.cond_text = name, ctype, power, condition_func, cond_text

# 役判定関数
def check_pair(d): return any(d.count(x) >= 2 for x in set(d))
def check_three(d): return any(d.count(x) >= 3 for x in set(d))
def check_straight(d): 
    s = sorted(list(set(d)))
    return any(s[i:i+5] == list(range(s[i], s[i]+5)) for i in range(len(s)-4))
def check_yahtzee(d): return len(set(d)) == 1 and d[0] != 0

# カードDB (30枚以上)
CARD_DB = {
    "ジェミニ・ダガー": Card("ジェミニ・ダガー", "attack", 15, check_pair, "ペア"),
    "トライ・ブラスト": Card("トライ・ブラスト", "attack", 25, check_three, "スリーカード"),
    "慈悲 of 祝福": Card("慈悲 of 祝福", "heal", 30, check_pair, "ペア"),
    "五行封印斬": Card("五行封印斬", "attack", 60, check_yahtzee, "ヤッツィー"),
    "スカイ・ストライク": Card("スカイ・ストライク", "attack", 40, check_straight, "L・ストレート"),
    "聖なる祈り": Card("聖なる祈り", "heal", 50, lambda d: d.count(1) >= 2 or d.count(6) >= 2, "1か6のペア"),
    "ハイ・ローラー": Card("ハイ・ローラー", "attack", 50, lambda d: sum(d) >= 25, "合計25以上"),
    "偶数の審判": Card("偶数の審判", "attack", 40, lambda d: all(x % 2 == 0 for x in d if x != 0), "すべて偶数"),
    # (他のカードも同様に追加可能)
}

INNATE_DECK = [
    Card("固有:トリニティ", "attack", 20, check_three, "スリーカード"),
    Card("固有:五連光破斬", "attack", 30, check_straight, "ストレート"),
    Card("固有:神罰 of 五連星", "attack", 50, check_yahtzee, "ヤッツィー")
]

# --- 3. DB操作関数 ---
def get_data():
    res = supabase.table("game_state").select("*").eq("id", 1).execute()
    if not res.data:
        st.error("データ(ID:1)が見つかりません。リセットボタンを押すかSQLを確認してください。")
        st.stop()
    return res.data[0]

def update_db(u):
    try: supabase.table("game_state").update(u).eq("id", 1).execute()
    except Exception as e: st.error(f"DBエラー: {e}")

# --- 4. UIデザイン ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    .hp-bar-container { background: #333; height: 10px; border-radius: 5px; margin-top: 5px; }
    .hp-bar-fill { background: #00FFAA; height: 100%; border-radius: 5px; transition: width 0.5s; }
    .dice-slot {
        background: rgba(0, 0, 0, 0.5); border: 2px solid #00FFFF; border-radius: 10px;
        height: 80px; display: flex; align-items: center; justify-content: center;
        font-size: 35px; color: #00FFFF; box-shadow: 0 0 15px rgba(0, 255, 255, 0.3);
    }
    .opp-dice { border-color: #FF4B4B; color: #FF4B4B; height: 50px; font-size: 20px; opacity: 0.7; }
    div.stButton > button { background-color: #FF5555 !important; color: white !important; width: 100% !important; font-weight: bold !important; }
    .skill-card { border: 1px solid #FF5555; border-radius: 10px; padding: 15px; background: #1A1C23; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 5. ゲームロジック ---
data = get_data()
role = st.sidebar.radio("役割を選択", ["Player 1", "Player 2"])
me, opp, my_id, opp_id = ("p1", "p2", 1, 2) if role == "Player 1" else ("p2", "p1", 2, 1)

st.title("⚔️ YAHTZEE TACTICS ⚔️")

# ステータス表示
c1, c2 = st.columns(2)
for p_num in [1, 2]:
    with (c1 if p_num == 1 else c2):
        hp = data[f"hp{p_num}"]
        st.write(f"PLAYER {p_num} {'🔥' if data['turn'] == f'P{p_num}' else ''}")
        st.markdown(f"<div class='hp-bar-container'><div class='hp-bar-fill' style='width:{(hp/150)*100}%'></div></div>", unsafe_allow_html=True)

# 相手のダイス
st.write(f"### 🛡️ 相手(P{opp_id})の刻印")
o_dice = data.get(f"{opp}_dice", [0,0,0,0,0])
oc = st.columns(5)
for i in range(5): oc[i].markdown(f"<div class='dice-slot opp-dice'>{o_dice[i]}</div>", unsafe_allow_html=True)

st.divider()

is_my_turn = (data["turn"] == f"P{my_id}")

if is_my_turn:
    if st.session_state.get("last_processed_turn") != data["turn_count"]:
        st.session_state.dice = [random.randint(1, 6) for _ in range(5)]
        st.session_state.rolls = 2
        st.session_state.keep = [False]*5
        st.session_state.last_processed_turn = data["turn_count"]
        update_db({f"{me}_dice": st.session_state.dice})
        st.rerun()

    st.write("### 🎲 運命の刻印")
    dc = st.columns(5)
    for i in range(5):
        dc[i].markdown(f"<div class='dice-slot'>{st.session_state.dice[i]}</div>", unsafe_allow_html=True)
        st.session_state.keep[i] = dc[i].checkbox("Keep", key=f"k{i}_{data['turn_count']}")

    if st.session_state.rolls > 0:
        if st.button(f"もう一度振る (残り{st.session_state.rolls}回)", key=f"re_{data['turn_count']}"):
            for i in range(5):
                if not st.session_state.keep[i]: st.session_state.dice[i] = random.randint(1, 6)
            st.session_state.rolls -= 1
            update_db({f"{me}_dice": st.session_state.dice})
            st.rerun()
else:
    st.session_state.dice = [0,0,0,0,0]
    st.info("相手のターンです...")

# 手札表示
st.write("### ⚔️ あなたのスキル")
my_hand = data.get(f"{me}_hand", [])
used_innate = data.get(f"{me}_used_innate", [])
pool = [c for c in INNATE_DECK if c.name not in used_innate]
for h_name in my_hand:
    if h_name in CARD_DB: pool.append(CARD_DB[h_name])

sc = st.columns(3)
for idx, card in enumerate(pool):
    is_ready = card.condition_func(st.session_state.dice) if is_my_turn else False
    with sc[idx % 3]:
        st.markdown(f"<div class='skill-card' style='border-color: {'#00FFAA' if is_ready else '#FF5555'};'><b>{card.name}</b><br><small>{card.cond_text}</small></div>", unsafe_allow_html=True)
        if is_my_turn and is_ready:
            if st.button("発動", key=f"atk_{idx}_{data['turn_count']}"):
                upd = {"turn": f"P{opp_id}", "turn_count": data["turn_count"]+1}
                if card.type == "attack": upd[f"hp{opp_id}"] = data[f"hp{opp_id}"] - card.power
                else: upd[f"hp{my_id}"] = data[f"hp{my_id}"] + card.power
                if "固有" in card.name: upd[f"{me}_used_innate"] = used_innate + [card.name]
                else:
                    my_hand.remove(card.name)
                    upd[f"{me}_hand"] = my_hand
                update_db(upd); st.rerun()

if is_my_turn:
    if st.button("ターン終了 & ドロー", key=f"draw_{data['turn_count']}"):
        latest = get_data()
        deck = latest.get("deck", [])
        hand = latest.get(f"{me}_hand", [])
        if deck and len(hand) < 5: hand.append(deck.pop(0))
        update_db({"deck": deck, f"{me}_hand": hand, "turn": f"P{opp_id}", "turn_count": data["turn_count"]+1})
        st.rerun()
else:
    time.sleep(3)
    st.rerun()

if st.sidebar.button("🚨 全リセット"):
    all_cards = list(CARD_DB.keys())
    new_deck = all_cards * 2
    random.shuffle(new_deck)
    update_db({"hp1": 150, "hp2": 150, "turn": "P1", "turn_count": 0, "p1_hand": [], "p2_hand": [], "p1_used_innate": [], "p2_used_innate": [], "p1_dice": [1,1,1,1,1], "p2_dice": [1,1,1,1,1], "deck": new_deck})
    st.rerun()
