import streamlit as st
from supabase import create_client
import time
import random

# --- 1. Supabase 接続 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. 状態異常処理ロジック ---
def apply_status_effects(current_hp, status_dict):
    """状態異常ダメージを計算し、残りターンを減らす"""
    new_hp = current_hp
    new_status = {}
    logs = []
    
    for effect, turns in status_dict.items():
        if turns > 0:
            if effect == "poison":
                dmg = 10
                new_hp -= dmg
                logs.append(f"🧪 毒ダメージ: {dmg}!")
            elif effect == "burn":
                dmg = 15
                new_hp -= dmg
                logs.append(f"🔥 燃焼ダメージ: {dmg}!")
            
            if turns - 1 > 0:
                new_status[effect] = turns - 1
    
    return max(0, new_hp), new_status, logs

# --- 3. 同期関数 ---
def get_data():
    res = supabase.table("game_state").select("*").eq("id", 1).execute()
    return res.data[0]

def update_game(update_dict):
    supabase.table("game_state").update(update_dict).eq("id", 1).execute()

# --- 4. メメインUI ---
st.set_page_config(page_title="Yahtzee Tactics Online", layout="wide")
data = get_data()

role = st.sidebar.radio("役割", ["Player 1", "Player 2"])
my_id = "P1" if role == "Player 1" else "P2"
enemy_id = "P2" if role == "Player 1" else "P1"
my_hp_key = "hp1" if role == "Player 1" else "hp2"
enemy_hp_key = "hp2" if role == "Player 1" else "hp1"
my_status_key = "p1_status" if role == "Player 1" else "p2_status"
enemy_status_key = "p2_status" if role == "Player 1" else "p1_status"

st.title("⚔️ Yahtzee Online: Status Effects")

# ステータス表示
c1, c2 = st.columns(2)
with c1:
    st.metric("P1 HP", data["hp1"])
    st.write(f"状態: {data['p1_status']}")
with c2:
    st.metric("P2 HP", data["hp2"])
    st.write(f"状態: {data['p2_status']}")

# --- 5. ターン開始時の状態異常チェック ---
# 自分のターンになった瞬間、一度だけダメージ処理を行うための判定
if data["turn"] == my_id:
    # 前回のダメージ処理が済んでいないかチェック（Session Stateを利用）
    if st.session_state.get("last_processed_turn") != data.get("turn_count", 0):
        new_hp, new_status, logs = apply_status_effects(data[my_hp_key], data[my_status_key])
        if logs:
            for log in logs: st.toast(log)
            # データベースを更新（ダメージとターン減少）
            update_game({my_hp_key: new_hp, my_status_key: new_status})
            st.rerun()
        st.session_state["last_processed_turn"] = data.get("turn_count", 0)

    st.success("あなたの番です！")
    
    # 攻撃デモ用ボタン（本来はダイス判定後に実行）
    if st.button("相手を「毒(3T)」にする攻撃！"):
        update_game({
            enemy_status_key: {"poison": 3},
            "turn": enemy_id,
            "turn_count": data.get("turn_count", 0) + 1
        })
        st.rerun()

    if st.button("何もしないで交代"):
        update_game({
            "turn": enemy_id,
            "turn_count": data.get("turn_count", 0) + 1
        })
        st.rerun()

else:
    st.info("相手の行動を待っています...")
    time.sleep(3)
    st.rerun()

# リセット
if st.sidebar.button("♻️ フルリセット"):
    update_game({
        "hp1": 100, "hp2": 100, 
        "turn": "P1", "turn_count": 0,
        "p1_status": {}, "p2_status": {},
        "deck": [] # 前回の山札初期化関数をここに呼ぶ
    })
    st.rerun()
