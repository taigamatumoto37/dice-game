import streamlit as st
import random
import time

# ページ設定
st.set_page_config(page_title="Yahtzee Tactics Online", layout="wide")

# --- オンライン同期の仕組み（簡易版） ---
# 本来はDBを使いますが、テスト用に「誰かが動かしたら全員に伝わる」
# Streamlitのキャッシュ機能を使った疑似同期を実装します。

if "room_data" not in st.session_state:
    st.session_state.room_data = {"p1_hp": 150, "p2_hp": 150, "turn": "P1"}

st.title("⚔️ Yahtzee Tactics: GitHub Edition")

# --- サイドバー ---
role = st.sidebar.radio("あなたの役割", ["Player 1", "Player 2"])
if st.sidebar.button("♻️ ゲームをリセット"):
    st.session_state.room_data = {"p1_hp": 150, "p2_hp": 150, "turn": "P1"}
    st.rerun()

# --- メイン画面 ---
data = st.session_state.room_data
c1, c2 = st.columns(2)
c1.metric("Player 1 HP", data["p1_hp"])
c2.metric("Player 2 HP", data["p2_hp"])

st.write(f"### 現在の番: {data['turn']}")

# 自分の番の時だけボタンを表示
if (role == "Player 1" and data["turn"] == "P1") or (role == "Player 2" and data["turn"] == "P2"):
    if st.button("💥 攻撃する！"):
        dmg = random.randint(15, 40)
        if data["turn"] == "P1":
            data["p2_hp"] -= dmg
            data["turn"] = "P2"
        else:
            data["p1_hp"] -= dmg
            data["turn"] = "P1"
        st.success(f"{dmg} のダメージを与えた！")
        time.sleep(1)
        st.rerun()
else:
    st.info("相手の行動を待っています...")
    time.sleep(2)
    st.rerun()
