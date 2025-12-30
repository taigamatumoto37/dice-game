import streamlit as st
from supabase import create_client
import time
import random

# --- 1. Supabase 接続 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. カードマスターデータ (tttt.py の全データを完全再現) ---
CARD_MASTER = {
    "ジェミニ・ダガー": {"type": "attack", "pwr": 15, "cond": "pair", "rarity": "弱"},
    "トライ・ブラスト": {"type": "attack", "pwr": 25, "cond": "three", "rarity": "中"},
    "崩壊の紫煙(毒)": {"type": "status", "pwr": 0, "cond": "three", "rarity": "中", "effect": ["poison", 3]},
    "天階の連撃": {"type": "attack", "pwr": 40, "cond": "straight", "rarity": "強"},
    "煉獄の業火(炎)": {"type": "status", "pwr": 0, "cond": "straight", "rarity": "強", "effect": ["burn", 2]},
    "慈悲の祝福": {"type": "heal", "pwr": 30, "cond": "pair", "rarity": "レア"},
    "終焉の聖家": {"type": "attack", "pwr": 60, "cond": "full_house", "rarity": "レア"},
    "固有:神罰の五連星": {"type": "attack", "pwr": 50, "cond": "yahtzee", "rarity": "固有"}
}

# 役判定関数 (tttt.py 移植)
def check_dice(dice, condition):
    if condition == "pair": return any(dice.count(x) >= 2 for x in set(dice))
    if condition == "three": return any(dice.count(x) >= 3 for x in set(dice))
    if condition == "straight": 
        s = sorted(list(set(dice)))
        return any(s[i:i+5] == list(range(s[i], s[i]+5)) for i in range(len(s)-4))
    if condition == "full_house":
        counts = [dice.count(x) for x in set(dice)]
        return 3 in counts and 2 in counts
    if condition == "yahtzee": return len(set(dice)) == 1
    return False

# --- 3. 山札作成関数 (全60枚のデッキ構成) ---
def create_full_deck():
    deck = []
    deck += ["ジェミニ・ダガー"] * 20
    deck += ["トライ・ブラスト"] * 16
    deck += ["崩壊の紫煙(毒)"] * 2
    deck += ["天階の連撃"] * 10
    deck += ["煉獄の業火(炎)"] * 2
    deck += ["慈悲の祝福"] * 5
    deck += ["終焉の聖家"] * 5
    random.shuffle(deck)
    return deck

# --- 4. 同期関数 ---
def get_data():
    return supabase.table("game_state").select("*").eq("id", 1).execute().data[0]

def update_game(update_dict):
    supabase.table("game_state").update(update_dict).eq("id", 1).execute()

# --- 5. メイン画面 ---
st.set_page_config(page_title="Yahtzee Battle Tactics Online", layout="wide")
data = get_data()

role = st.sidebar.radio("あなたの役割", ["Player 1", "Player 2"])
my_id = "P1" if role == "Player 1" else "P2"
enemy_id = "P2" if role == "Player 1" else "P1"
my_hp_key, enemy_hp_key = ("hp1", "hp2") if role == "Player 1" else ("hp2", "hp1")
my_status_key, enemy_status_key = ("p1_status", "p2_status") if role == "Player 1" else ("p2_status", "p1_status")

st.title("🎲 Yahtzee Battle Tactics Online")

# 情報パネル
col1, col2, col3 = st.columns(3)
col1.metric("Player 1 HP", data["hp1"])
col2.metric("Player 2 HP", data["hp2"])
col3.metric("山札残り", len(data["deck"]))

# 自分のターン
if data["turn"] == my_id:
    st.success("あなたの番です！")
    
    if "my_hand" not in st.session_state: st.session_state.my_hand = []
    if "dice" not in st.session_state: st.session_state.dice = [1,1,1,1,1]

    # ダイス操作
    if st.button("🎲 ダイスを振る"):
        st.session_state.dice = [random.randint(1, 6) for _ in range(5)]
    st.write(f"### 出目: {' '.join([f'[{d}]' for d in st.session_state.dice])}")

    # アクション
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🎴 カードをドローして終了"):
            deck = data["deck"]
            if deck:
                new_card = deck.pop()
                st.session_state.my_hand.append(new_card)
                update_game({"deck": deck, "turn": enemy_id, "turn_count": data["turn_count"]+1})
                st.rerun()
    
    with c2:
        # 手札から使用
        if st.session_state.my_hand:
            use_card = st.selectbox("使うカードを選択:", st.session_state.my_hand)
            card_info = CARD_MASTER[use_card]
            if st.button(f"🔥 {use_card} を発動！"):
                if check_dice(st.session_state.dice, card_info["cond"]):
                    # 効果適用
                    updates = {"turn": enemy_id, "turn_count": data["turn_count"]+1}
                    if card_info["type"] == "attack":
                        updates[enemy_hp_key] = max(0, data[enemy_hp_key] - card_info["pwr"])
                    elif card_info["type"] == "heal":
                        updates[my_hp_key] = min(100, data[my_hp_key] + card_info["pwr"])
                    elif card_info["type"] == "status":
                        updates[enemy_status_key] = {card_info["effect"][0]: card_info["effect"][1]}
                    
                    st.session_state.my_hand.remove(use_card)
                    update_game(updates)
                    st.rerun()
                else:
                    st.error("役が揃っていません！")

else:
    st.info("相手が戦略を練っています...")
    time.sleep(3)
    st.rerun()

# --- 6. リセットボタン (全カード詰め込み) ---
if st.sidebar.button("♻️ ゲームをフルリセット"):
    update_game({
        "hp1": 100, "hp2": 100,
        "turn": "P1", "turn_count": 0,
        "p1_status": {}, "p2_status": {},
        "deck": create_full_deck()
    })
    st.session_state.my_hand = []
    st.rerun()

st.sidebar.write("### あなたの手札")
for c in st.session_state.my_hand:
    st.sidebar.info(f"{c}\n({CARD_MASTER[c]['rarity']})")
