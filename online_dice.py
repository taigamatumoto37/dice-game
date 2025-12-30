import streamlit as st
from supabase import create_client
import time
import random

# --- 1. Supabase 接続 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. カード定義 (tttt.pyの移植) ---
def check_pair(d): return any(d.count(x) >= 2 for x in set(d))
def check_three(d): return any(d.count(x) >= 3 for x in set(d))
def check_straight(d): 
    s = sorted(list(set(d)))
    return any(s[i:i+5] == list(range(s[i], s[i]+5)) for i in range(len(s)-4))
def check_full_house(d): 
    counts = [d.count(x) for x in set(d)]
    return 3 in counts and 2 in counts
def check_yahtzee(d): return len(set(d)) == 1

# カードマスタ（名前: [タイプ, 威力, 役名, 状態異常, レア度]）
CARD_MASTER = {
    "ジェミニ・ダガー": ["attack", 15, "pair", None, "弱"],
    "トライ・ブラスト": ["attack", 25, "three", None, "中"],
    "崩壊の紫煙(毒)": ["status", 0, "three", ("poison", 3), "中"],
    "天階の連撃": ["attack", 40, "straight", None, "強"],
    "慈悲の祝福": ["heal", 30, "pair", None, "レア"],
    "終焉の聖家": ["attack", 60, "full_house", None, "レア"],
    "固有:神罰の五連星": ["attack", 50, "yahtzee", None, "固有"]
}

# --- 3. 同期関数 ---
def get_data():
    res = supabase.table("game_state").select("*").eq("id", 1).execute()
    return res.data[0]

def update_game(update_dict):
    supabase.table("game_state").update(update_dict).eq("id", 1).execute()

# 山札の作成
def create_new_deck():
    d = []
    for name in CARD_MASTER:
        if "固有" not in name:
            d.extend([name] * 5) # 各5枚ずつ
    random.shuffle(d)
    return d

# --- 4. メインUI ---
st.set_page_config(page_title="Yahtzee Tactics Online", layout="wide")
data = get_data()

# プレイヤー設定
role = st.sidebar.radio("役割", ["Player 1", "Player 2"])
my_id = "P1" if role == "Player 1" else "P2"
enemy_id = "P2" if role == "Player 1" else "P1"
my_hp_key = "hp1" if role == "Player 1" else "hp2"
enemy_hp_key = "hp2" if role == "Player 1" else "hp1"

st.title("⚔️ Yahtzee Online: Deck Sync")

# ステータス表示
c1, c2 = st.columns(2)
c1.metric("P1 HP", data["hp1"])
c2.metric("P2 HP", data["hp2"])
st.write(f"🎴 山札残り: {len(data['deck'] if data['deck'] else [])} 枚")

# 自分のターン
if data["turn"] == my_id:
    st.success("あなたの番です！")
    
    # 手札の管理 (Session State)
    if "my_hand" not in st.session_state: st.session_state.my_hand = []
    if "dice" not in st.session_state: st.session_state.dice = [random.randint(1,6) for _ in range(5)]

    st.write(f"### 🎲 ダイス: {st.session_state.dice}")
    
    col_a, col_b, col_c = st.columns(3)
    
    # 1. 振り直し
    if col_a.button("振り直す"):
        st.session_state.dice = [random.randint(1,6) for _ in range(5)]
        st.rerun()

    # 2. ドロー（共通の山札から引く）
    if col_b.button("カードを1枚引く"):
        deck = data["deck"]
        if deck:
            new_card = deck.pop()
            st.session_state.my_hand.append(new_card)
            update_game({"deck": deck, "turn": enemy_id})
            st.rerun()
        else:
            st.error("山札がありません！")

    # 3. 攻撃（手札から選ぶ）
    if st.session_state.my_hand:
        selected = st.selectbox("手札から技を使う:", st.session_state.my_hand)
        if st.button("発動！"):
            m = CARD_MASTER[selected]
            # 役判定
            cond_func = {"pair": check_pair, "three": check_three, "straight": check_straight, "full_house": check_full_house, "yahtzee": check_yahtzee}[m[2]]
            
            if cond_func(st.session_state.dice):
                dmg = m[1]
                new_enemy_hp = data[enemy_hp_key] - dmg
                st.session_state.my_hand.remove(selected)
                update_game({enemy_hp_key: max(0, new_enemy_hp), "turn": enemy_id})
                st.rerun()
            else:
                st.error("役が足りません！")

else:
    st.info("相手がドローまたは攻撃を考えています...")
    time.sleep(3)
    st.rerun()

# リセット
if st.sidebar.button("♻️ ゲームリセット"):
    update_game({"hp1": 100, "hp2": 100, "turn": "P1", "deck": create_new_deck()})
    st.rerun()
