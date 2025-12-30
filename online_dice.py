import streamlit as st
from supabase import create_client
import time
import random

# --- 1. Supabase 接続設定 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. カード・役判定ロジック (tttt.py 完全再現) ---
def check_pair(d): return any(d.count(x) >= 2 for x in set(d))
def check_three(d): return any(d.count(x) >= 3 for x in set(d))
def check_straight(d): 
    s = sorted(list(set(d)))
    return any(s[i:i+5] == list(range(s[i], s[i]+5)) for i in range(len(s)-4))
def check_full_house(d): 
    counts = [d.count(x) for x in set(d)]
    return 3 in counts and 2 in counts
def check_yahtzee(d): return len(set(d)) == 1

# カードクラスの定義
class Card:
    def __init__(self, name, ctype, power, condition_key, rarity, status_effect=None):
        self.name = name
        self.type = ctype
        self.power = power
        self.condition_key = condition_key
        self.rarity = rarity
        self.status_effect = status_effect

    def check(self, dice):
        funcs = {"pair": check_pair, "three": check_three, "straight": check_straight, 
                 "full_house": check_full_house, "yahtzee": check_yahtzee}
        return funcs[self.condition_key](dice)

# カードマスタ
INNATE_CARDS = [
    Card("固有:トリニティ・インパクト", "attack", 20, "three", "固有"),
    Card("固有:五連光破斬", "attack", 25, "straight", "固有"),
    Card("固有:神罰の五連星", "attack", 50, "yahtzee", "固有")
]

# --- 3. データベース同期関数 ---
def get_data():
    return supabase.table("game_state").select("*").eq("id", 1).execute().data[0]

def update_db(updates):
    supabase.table("game_state").update(updates).eq("id", 1).execute()

def create_initial_deck():
    d = (["ジェミニ・ダガー"] * 20 + ["トライ・ブラスト"] * 16 + ["崩壊の紫煙(毒)"] * 2 + 
         ["天階の連撃"] * 10 + ["煉獄の業火(炎)"] * 2 + ["慈悲の祝福"] * 5 + ["終焉の聖家"] * 5)
    random.shuffle(d)
    return d

CARD_DB = {
    "ジェミニ・ダガー": Card("ジェミニ・ダガー", "attack", 15, "pair", "弱"),
    "トライ・ブラスト": Card("トライ・ブラスト", "attack", 25, "three", "中"),
    "崩壊の紫煙(毒)": Card("崩壊の紫煙(毒)", "status", 0, "three", "中", ["poison", 3]),
    "天階の連撃": Card("天階の連撃", "attack", 40, "straight", "強"),
    "煉獄の業火(炎)": Card("煉獄の業火(炎)", "status", 0, "straight", "強", ["burn", 2]),
    "慈悲の祝福": Card("慈悲の祝福", "heal", 30, "pair", "レア"),
    "終焉の聖家": Card("終焉の聖家", "attack", 60, "full_house", "レア")
}

# --- 4. メインUI ---
st.set_page_config(page_title="Yahtzee Battle Tactics", layout="wide")
data = get_data()

# 役割とキーの設定
role = st.sidebar.radio("役割", ["Player 1", "Player 2"])
me = "p1" if role == "Player 1" else "p2"
opp = "p2" if role == "Player 1" else "p1"
my_turn_id = "P1" if role == "Player 1" else "P2"

st.title("🎲 Yahtzee Battle Tactics Online")

# プレイヤー情報表示 (tttt.py UI再現)
col1, col2 = st.columns(2)
for i, p_id in enumerate(["p1", "p2"]):
    with (col1 if i == 0 else col2):
        st.subheader(f"PLAYER {i+1}" + (" (手番)" if data["turn"] == f"P{i+1}" else ""))
        hp = data[f"hp{i+1}"]
        st.progress(max(0, hp) / 100)
        st.write(f"❤️ HP: {hp}/100 | ⚔️ Bonus: +{data.get(f'{p_id}_bonus', 0)}")
        # 状態異常表示
        st_info = data.get(f"{p_id}_status", {})
        st.write(f"⚠️ 状態: {st_info if st_info else 'なし'}")

st.divider()

# --- 5. ゲーム進行 ---
if data["turn"] == my_turn_id:
    # A. ターン開始時：状態異常ダメージ処理
    if st.session_state.get("turn_processed") != data["turn_count"]:
        my_st = data.get(f"{me}_status", {})
        new_hp = data[f"hp{1 if me=='p1' else 2}"]
        new_status = {}
        for s, t in my_st.items():
            if t > 0:
                dmg = 5 if s == "poison" else 10
                new_hp -= dmg
                st.toast(f"{s}ダメージ: {dmg}")
                if t-1 > 0: new_status[s] = t-1
        update_db({f"hp{1 if me=='p1' else 2}": max(0, new_hp), f"{me}_status": new_status})
        st.session_state["turn_processed"] = data["turn_count"]
        st.rerun()

    # B. ダイスフェーズ
    if "dice" not in st.session_state: st.session_state.dice = [random.randint(1,6) for _ in range(5)]
    st.write(f"### 🎲 ダイス: {' '.join([f'[{d}]' for d in st.session_state.dice])}")
    
    # C. 行動選択
    if "my_hand" not in st.session_state: st.session_state.my_hand = []
    
    c1, c2, c3 = st.columns(3)
    if c1.button("1回振り直す"):
        st.session_state.dice = [random.randint(1,6) for _ in range(5)]
        st.rerun()

    if len(st.session_state.my_hand) < 5:
        if c2.button("カードをドローして終了"):
            deck = data["deck"]
            if deck:
                card_name = deck.pop()
                st.session_state.my_hand.append(card_name)
                update_db({"deck": deck, "turn": "P2" if my_turn_id=="P1" else "P1", "turn_count": data["turn_count"]+1})
                st.rerun()

# --- D. 攻撃フェーズの正しい構造 ---
    if not available:
        st.error("揃っている役がありません。カードを引くか、振り直してください。")
    else:
        # 役がある場合の処理（ここは一発インデントを下げる）
        options = {f"{c.name} ({c.rarity})": c for c in available}
        selected_label = st.radio("使用する技を選択:", list(options.keys()))
        selected_card = options[selected_label]

        if st.button(f"🔥 {selected_card.name} を発動！"):
            bonus = data.get(f"{me}_bonus", 0)
            updates = {
                "turn": "P2" if my_turn_id=="P1" else "P1", 
                "turn_count": data["turn_count"] + 1
            }
            
            # 効果の適用
            if selected_card.type == "attack":
                dmg = selected_card.power + bonus
                target_hp_key = "hp2" if me == "p1" else "hp1"
                updates[target_hp_key] = max(0, data[target_hp_key] - dmg)
            
            elif selected_card.type == "heal":
                my_hp_key = "hp1" if me == "p1" else "hp2"
                updates[my_hp_key] = min(100, data[my_hp_key] + selected_card.power)
                
            elif selected_card.type == "status":
                s_name, s_turn = selected_card.status_effect
                updates[f"{opp}_status"] = {s_name: s_turn}

            # 消費処理
            if "固有" in selected_card.name:
                new_used = used_innate + [selected_card.name]
                if len(new_used) >= 3:
                    updates[f"{me}_bonus"] = bonus + 10
                    updates[f"{me}_used_innate"] = []
                else:
                    updates[f"{me}_used_innate"] = new_used
            else:
                st.session_state.my_hand.remove(selected_card.name)
            
            update_db(updates)
            st.rerun()

# サイドバー：手札とリセット
st.sidebar.write("### 🃏 あなたの手札")
for h in st.session_state.get("my_hand", []):
    st.sidebar.info(h)

if st.sidebar.button("♻️ フルリセット"):
    update_db({
        "hp1": 100, "hp2": 100, "turn": "P1", "turn_count": 0,
        "p1_status": {}, "p2_status": {}, "p1_bonus": 0, "p2_bonus": 0,
        "p1_used_innate": [], "p2_used_innate": [], "deck": create_initial_deck()
    })
    st.session_state.my_hand = []
    st.rerun()


