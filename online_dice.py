import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

st.set_page_config(page_title="Yahtzee Tactics Online")

# スプレッドシートへの接続
conn = st.connection("gsheets", type=GSheetsConnection)

# データの読み込み
def load_data():
    return conn.read(worksheet="Sheet1", ttl=0)

df = load_data()
p1_hp = df.at[0, "hp1"]
p2_hp = df.at[0, "hp2"]
turn = df.at[0, "turn"]

st.title("⚔️ G-Sheet Battle Online")

role = st.sidebar.radio("役割", ["Player 1", "Player 2"])

c1, c2 = st.columns(2)
c1.metric("P1 HP", p1_hp)
c2.metric("P2 HP", p2_hp)

is_my_turn = (role == "Player 1" and turn == "P1") or (role == "Player 2" and turn == "P2")

if is_my_turn:
    if st.button("攻撃！"):
        # データの更新処理
        new_df = pd.DataFrame([{
            "hp1": p1_hp if role == "Player 1" else p1_hp - 20,
            "hp2": p2_hp - 20 if role == "Player 1" else p2_hp,
            "turn": "P2" if turn == "P1" else "P1"
        }])
        conn.update(worksheet="Sheet1", data=new_df)
        st.success("攻撃完了！")
        time.sleep(1)
        st.rerun()
else:
    st.info("相手を待っています...")
    time.sleep(3)
    st.rerun()
