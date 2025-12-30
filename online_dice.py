import streamlit as st
from supabase import create_client
import time
import random

# --- 1. Supabase 接続 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. カード・判定定義 ---
class Card:
    def __init__(self, name, ctype, power, condition_func, cond_text):
        self.name, self.type, self.power, self.condition_func, self.cond_text = name, ctype, power, condition_func, cond_text

def check_pair(d): return any(d.count(x) >= 2 for x in set(d))
def check_three(d): return any(d.count(x) >= 3 for x in set(d))
def check_straight(d): 
    s = sorted(list(set(d)))
    return any(s[i:i+5] == list(range(s[i], s[i]+5)) for i in range(len(s)-4))
def check_yahtzee(d): return len(set(d)) == 1

CARD_DB = {
    "ジェミニ・ダガー": Card("ジェミニ・ダガー", "attack", 15, check_pair, "ペア"),
    "トライ・ブラスト": Card("トライ・ブラスト", "attack", 25, check_three, "スリーカード"),
    "慈悲 of 祝福": Card("慈悲 of 祝福", "heal", 35, check_pair, "ペア"),
}
INNATE_DECK = [
    Card("固有:トリニティ", "attack", 20, check_three, "スリーカード"),
    Card("固有:五連光破斬", "attack", 30, check_straight, "ストレート"),
    Card("固有:神罰の五連星", "attack", 50, check_yahtzee, "ヤッツィー")
]

def get_data(): return supabase.table("game_state").select("*").eq("id", 1).execute().data[0]
def update_db(u): 
    try: supabase.table("game_state").update(u).eq("id", 1).execute()
    except: pass

# --- 3. 画像に基づいたCSS再現 ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    
    /* HPバー */
    .hp-bar-container { background: #333; height: 10px; border-radius: 5px; margin-top: 5px; }
    .hp-bar-fill { background: #00FFAA; height: 100%; border-radius: 5px; transition: width 0.5s; }
    
    /* ダイス外枠 (ネオンブルー) */
    .dice-slot {
        background: rgba(0, 0, 0, 0.5);
        border: 2px solid #00FFFF;
        border-radius: 10px;
        height: 80px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 35px;
        color: #00FFFF;
        box-shadow: 0 0 15px rgba(0, 255, 255, 0.3);
    }
    .opp-dice { border-color: #FF4B4B; color: #FF4B4B; height: 50px; font-size: 20px; box-shadow: none; opacity: 0.7; }

    /* 赤色横長ボタン (振り直し・発動) */
    div.stButton > button {
        background-color: #FF5555 !important;
        color: white !important;
        width: 100% !important;
        border-radius: 5px !important;
        border: none !important;
        font-weight: bold !important;
    }
    
    /* スキルカード */
    .skill-card {
        border: 1px solid #FF5555;
        border-radius: 10px;
        padding: 15px;
        background: #1A1C23;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. メイン処理 ---
data = get_data()
role = st.sidebar.radio("役割を選択", ["Player 1", "Player 2"])
me, opp, my_id, opp_id = ("p1", "p2", 1, 2) if role == "Player 1" else ("p2", "p1", 2, 1)

st.title("⚔️ YAHTZEE TACTICS ⚔️")

# --- ステータスエリア ---
c1, c2 = st.columns(2)
for p_num in [1, 2]:
    with (c1 if p_num == 1 else c2):
        hp = data[f"hp{p_num}"]
        st.write(f"PLAYER {p_num} {'🔥' if data['turn'] == f'P{p_num}' else ''}")
        st.write(f"HP {hp} / 150")
        st.markdown(f"<div class='hp-bar-container'><div class='hp-bar-fill' style='width:{(hp/150)*100}%'></div></div>", unsafe_allow_html=True)

# --- 相手のダイス表示 (リアルタイム) ---
st.write(f"### 🛡️ 相手(P{opp_id})の刻印")
o_dice = data.get(f"{opp}_dice", [1,1,1,1,1])
oc = st.columns(5)
for i in range(5):
    oc[i].markdown(f"<div class='dice-slot opp-dice'>{o_dice[i]}</div>", unsafe_allow_html=True)

st.divider()

# --- ターン管理 (ここから入れ替え) ---
is_my_turn = (data["turn"] == f"P{my_id}")

# 1. ターンの初期化処理
if is_my_turn:
    if st.session_state.get("last_processed_turn") != data["turn_count"]:
        st.session_state.dice = [random.randint(1, 6) for _ in range(5)]
        st.session_state.rolls = 2
        st.session_state.keep = [False] * 5
        st.session_state.last_processed_turn = data["turn_count"]
        update_db({f"{me}_dice": st.session_state.dice})
        st.rerun()

    st.write("### 🎲 運命の刻印")
    dc = st.columns(5)
    for i in range(5):
        dc[i].markdown(f"<div class='dice-slot'>{st.session_state.dice[i]}</div>", unsafe_allow_html=True)
        st.session_state.keep[i] = dc[i].checkbox("Keep", key=f"k{i}_{data['turn_count']}")

    if st.session_state.rolls > 0:
        if st.button(f"もう一度振る (残り{st.session_state.rolls}回)", key=f"reroll_{data['turn_count']}"):
            for i in range(5):
                if not st.session_state.keep[i]: st.session_state.dice[i] = random.randint(1, 6)
            st.session_state.rolls -= 1
            update_db({f"{me}_dice": st.session_state.dice})
            st.rerun()
else:
    # 相手のターン時は現在のダイスをクリア
    st.session_state.dice = [0,0,0,0,0] 
    st.info("相手のターンです。作戦を練りましょう...")

st.divider()

# 2. 自分のカード一覧（相手のターンでも表示）
st.write("### ⚔️ あなたのスキル")
used = data.get(f"{me}_used_innate", [])
hand = st.session_state.get("hand", [])
pool = [c for c in INNATE_DECK if c.name not in used]
for h in hand:
    if h in CARD_DB: pool.append(CARD_DB[h])

sc = st.columns(3)
for idx, card in enumerate(pool):
    # 自分のターンかつダイスがある時だけ役判定
    is_ready = card.condition_func(st.session_state.dice) if (is_my_turn and any(st.session_state.dice)) else False
    
    with sc[idx % 3]:
        st.markdown(f"""
        <div class='skill-card' style='border-color: {"#00FFAA" if is_ready else "#FF5555"};'>
            <b style='color: {"#00FFAA" if is_ready else "white"};'>{card.name}</b><br>
            <small>威力：{card.power} | 条件：{card.cond_text}</small>
        </div>
        """, unsafe_allow_html=True)
        
        # 自分のターン、かつ条件達成時のみ発動ボタン
        if is_my_turn and is_ready:
            if st.button("発動", key=f"atk_{idx}_{data['turn_count']}"):
                upd = {"turn": f"P{opp_id}", "turn_count": data["turn_count"]+1}
                if card.type == "attack": upd[f"hp{opp_id}"] = data[f"hp{opp_id}"] - card.power
                else: upd[f"hp{my_id}"] = data[f"hp{my_id}"] + card.power
                
                if "固有" in card.name:
                    new_used = used + [card.name]
                    upd[f"{me}_used_innate"] = [] if len(new_used) >= 3 else new_used
                else:
                    hand.remove(card.name)
                    st.session_state.hand = hand
                update_db(upd); st.rerun()

# 3. 終了処理と自動リロード
if is_my_turn:
    if st.button("ターンを終了してドロー", key=f"end_{data['turn_count']}"):
        latest = get_data()
        deck = latest.get("deck", [])
        if deck and len(hand) < 5:
            hand.append(deck.pop())
            st.session_state.hand = hand
        update_db({"deck": deck, "turn": f"P{opp_id}", "turn_count": latest["turn_count"]+1})
        st.rerun()
else:
    time.sleep(3)
    st.rerun()
# --- ここまで入れ替え ---
# 全リセット (サイドバー)
if st.sidebar.button("🚨 全リセット"):
    update_db({"hp1": 150, "hp2": 150, "turn": "P1", "turn_count": 0, "p1_used_innate": [], "p2_used_innate": [], "p1_dice": [1,1,1,1,1], "p2_dice": [1,1,1,1,1], "deck": ["ジェミニ・ダガー"]*10})
    st.session_state.hand = []; st.rerun()



