import streamlit as st
import random
import time

# ページ設定
st.set_page_config(page_title="Yahtzee Tactics Online", layout="wide")

st.title("⚔️ Yahtzee Tactics")

# --- データベースを使わず、自分のブラウザ内だけで動かす設定 ---
if "hp1" not in st.session_state:
    st.session_state.hp1 = 150
    st.session_state.hp2 = 150
    st.session_state.turn = "P1"

# サイドバー
role = st.sidebar.radio("あなたの役割", ["Player 1", "Player 2"])

# メイン表示
col1, col2 = st.columns(2)
col1.metric("Player 1 HP", st.session_state.hp1)
col2.metric("Player 2 HP", st.session_state.hp2)

st.write(f"### 現在の番: {st.session_state.turn}")

# 自分の番の判定
is_my_turn = (role == "Player 1" and st.session_state.turn == "P1") or \
             (role == "Player 2" and st.session_state.turn == "P2")

if is_my_turn:
    st.success("あなたの番です！")
    if st.button("💥 攻撃する！"):
        dmg = random.randint(15, 40)
        if role == "Player 1":
            st.session_state.hp2 -= dmg
            st.session_state.turn = "P2"
        else:
            st.session_state.hp1 -= dmg
            st.session_state.turn = "P1"
        st.toast(f"{dmg} のダメージ！")
        time.sleep(1)
        st.rerun()
else:
    st.info("相手の行動を待っています... (デモ版のため自分で役割を切り替えてください)")
