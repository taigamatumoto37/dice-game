import streamlit as st
from supabase import create_client
import time
import random
import json

# --- 1. Supabase 接続設定 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. 判定ロジック & カードクラス (tttt.pyより) ---
def check_pair(d): return any(d.count(x) >= 2 for x in set(d))
def check_three(d): return any(d.count(x) >= 3 for x in set(d))
def check_straight(d): 
    s = sorted(list(set(d)))
    return any(s[i:i+5] == list(range(s[i], s[i]+5)) for i in range(len(s)-4))
def check_full_house(d): 
    counts = [d.count(x) for x in set(d)]
    return 3 in counts and 2 in counts
def check_yahtzee(d): return len(set(d)) == 1

class Card:
    def __init__(self, name, ctype, power, condition_name, rarity, status_effect=None):
        self.name = name
        self.type = ctype
        self.power = power
        self.condition_name = condition_name
        self.rarity = rarity
        self.status_effect = status_effect

    def check_condition(self, dice):
        conds = {"pair": check_pair, "three": check_three, "straight": check_straight, 
                 "full_house": check_full_house, "yahtzee": check_yahtzee}
        return conds[self.condition_name](dice)

# カードデータの定義
innate_cards = [
    Card("固有:トリニティ", "attack", 20, "three", "固有"),
    Card("固有:五連光破斬", "attack", 25, "straight", "固有"),
    Card("固有:神罰の五連星", "attack", 50, "yahtzee", "固有")
]

# --- 3. データ同期用関数 ---
def get_game_state():
    res = supabase.table("game_state").select("*").eq("id", 1).execute()
    # Supabaseに保存できない複雑なデータ（手札など）はJSONとして扱う
    raw = res.data[0]
    return raw

def sync_update(update_dict):
    supabase.table("game_state").update(update_dict).eq("id", 1).execute()

# --- 4. メインUI ---
st.set_page_config(page_title="Yahtzee Tactics Online", layout="wide")
st.title("🎲 Yahtzee Battle Tactics Online")

data = get_game_state()
role = st.sidebar.radio("役割を選択", ["Player 1", "Player 2"])
my_id = "P1" if role == "Player 1" else "P2"
enemy_id = "P2" if role == "Player 1" else "P1"

# ステータス表示
col1, col2 = st.columns(2)
col1.metric("P1 HP", data["hp1"])
col2.metric("P2 HP", data["hp2"])

# --- 5. ゲームロジック ---
if data["turn"] == my_id:
    st.success("あなたの番です！")
    
    # フェーズ管理 (tttt.pyの仕組みを再現)
    if "phase" not in st.session_state: st.session_state.phase = "roll"
    if "dice" not in st.session_state: st.session_state.dice = [1,1,1,1,1]

    if st.session_state.phase == "roll":
        if st.button("ダイスを振る"):
            st.session_state.dice = [random.randint(1, 6) for _ in range(5)]
            st.session_state.phase = "action"
            st.rerun()

    elif st.session_state.phase == "action":
        st.write("### 🎲 ダイス: " + " ".join([f"[{d}]" for d in st.session_state.dice]))
        
        c1, c2 = st.columns(2)
        if c1.button("振り直す(1回限定)"):
            st.session_state.dice = [random.randint(1, 6) for _ in range(5)]
            st.rerun()
        
        # 簡易化した攻撃選択
        available = [c for c in innate_cards if c.check_condition(st.session_state.dice)]
        
        if not available:
            st.error("役が揃いませんでした...")
            if st.button("パスして交代"):
                sync_update({"turn": enemy_id})
                st.session_state.phase = "roll"
                st.rerun()
        else:
            selected = st.radio("技を選択:", available, format_func=lambda x: f"{x.name} (威力:{x.power})")
            if st.button("発動！"):
                dmg = selected.power
                new_hp1 = data["hp1"] - (dmg if my_id == "P2" else 0)
                new_hp2 = data["hp2"] - (dmg if my_id == "P1" else 0)
                
                sync_update({
                    "hp1": max(0, new_hp1),
                    "hp2": max(0, new_hp2),
                    "turn": enemy_id
                })
                st.session_state.phase = "roll"
                st.rerun()

# サイドバーにリセットボタン
if st.sidebar.button("♻️ ゲームリセット"):
    sync_update({"hp1": 100, "hp2": 100, "turn": "P1"})
    st.rerun()

# 待機中
if data["turn"] != my_id:
    st.info("相手が戦略を練っています...")
    time.sleep(3)
    st.rerun()
