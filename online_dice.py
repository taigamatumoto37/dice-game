import streamlit as st
from supabase import create_client
import time

# 接続
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def get_data():
    res = supabase.table("game_state").select("*").eq("id", 1).execute()
    return res.data[0]

def update_data(hp1, hp2, next_turn):
    supabase.table("game_state").update({"hp1": hp1, "hp2": hp2, "turn": next_turn}).eq("id", 1).execute()

# --- ゲーム画面 ---
data = get_data()
st.title("🎲 Online Yahtzee Battle")

role = st.sidebar.radio("役割", ["Player 1", "Player 2"])
col1, col2 = st.columns(2)
col1.metric("P1 HP", data["hp1"])
col2.metric("P2 HP", data["hp2"])

is_my_turn = (role == "Player 1" and data["turn"] == "P1") or (role == "Player 2" and data["turn"] == "P2")

if is_my_turn:
    if st.button("💥 攻撃！"):
        new_hp1 = data["hp1"] if role == "Player 1" else data["hp1"] - 20
        new_hp2 = data["hp2"] - 20 if role == "Player 1" else data["hp2"]
        update_data(new_hp1, new_hp2, "P2" if data["turn"] == "P1" else "P1")
        st.rerun()
else:
    st.info("相手のターンです...")
    time.sleep(2)
    st.rerun()
