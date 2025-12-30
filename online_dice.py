import streamlit as st
import random
import time

# ページの設定
st.set_page_config(page_title="Yahtzee Tactics", layout="wide")

# --- タイトル表示 ---
st.title("🎲 Yahtzee Tactics Online")

# --- サイドバーで設定 ---
st.sidebar.header("接続設定")
player_name = st.sidebar.text_input("プレイヤー名", value="Player1")
room_id = st.sidebar.text_input("ルーム番号(数字4桁)", value="1234")

# --- ゲームの状態を管理する箱（仮） ---
if 'hp' not in st.session_state:
    st.session_state.hp = 150
    st.session_state.enemy_hp = 150

# --- 画面の表示 ---
col1, col2 = st.columns(2)
with col1:
    st.metric(f"{player_name} (自分)", st.session_state.hp)
with col2:
    st.metric("相手プレイヤー", st.session_state.enemy_hp)

st.write("---")
if st.button("攻撃する！"):
    damage = random.randint(10, 30)
    st.session_state.enemy_hp -= damage
    st.success(f"{damage} のダメージを与えた！")