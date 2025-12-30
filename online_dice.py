import streamlit as st
from supabase import create_client
import time
import random

# --- 初期設定 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="Yahtzee Tactics Online", layout="wide")
st.title("🎲 Yahtzee Tactics Online")

# --- データの取得と更新関数 ---
def get_game_data():
    res = supabase.table("game_state").select("*").eq("id", 1).execute()
    return res.data[0]

def update_game(update_dict):
    supabase.table("game_state").update(update_dict).eq("id", 1).execute()

# --- 役の判定ロジック（簡易版） ---
def calculate_damage(dice):
    counts = {x: dice.count(x) for x in set(dice)}
    sorted_dice = sorted(list(set(dice)))
    
    # ヤッツィー (5つ同じ)
    if 5 in counts.values(): return 100, "ヤッツィー！(100点)"
    # フォーカード
    if 4 in counts.values(): return 40, "フォーカード！(40点)"
    # フルハウス
    if 3 in counts.values() and 2 in counts.values(): return 30, "フルハウス！(30点)"
    # ストレート (簡易判定)
    if len(sorted_dice) >= 4:
        for i in range(len(sorted_dice)-3):
            if sorted_dice[i:i+4] == list(range(sorted_dice[i], sorted_dice[i]+4)):
                return 25, "ストレート！(25点)"
    # 合計値
    return sum(dice), f"合計ダメージ({sum(dice)}点)"

# --- ゲーム画面 ---
data = get_game_data()
role = st.sidebar.radio("役割を選択", ["Player 1", "Player 2"])
my_id = "P1" if role == "Player 1" else "P2"
enemy_id = "P2" if role == "Player 1" else "P1"

# ステータス表示
col1, col2 = st.columns(2)
col1.metric("Player 1 HP", data["hp1"])
col2.metric("Player 2 HP", data["hp2"])

st.subheader(f"現在は {data['turn']} のターンです")

# セッション状態（ダイス管理）
if "my_dice" not in st.session_state:
    st.session_state.my_dice = [1, 2, 3, 4, 5]
    st.session_state.keeps = [False] * 5
    st.session_state.rolls_left = 3

# 自分のターンの処理
if data["turn"] == my_id:
    st.success("あなたの番です！")
    
    # ダイス表示とキープ選択
    cols = st.columns(5)
    for i in range(5):
        with cols[i]:
            st.button(f"🎲 {st.session_state.my_dice[i]}", key=f"dice_{i}", disabled=True)
            st.session_state.keeps[i] = st.checkbox("Keep", value=st.session_state.keeps[i], key=f"keep_{i}")

    # 操作ボタン
    col_a, col_b = st.columns(2)
    
    # 振るボタン
    if st.session_state.rolls_left > 0:
        if col_a.button(f"ダイスを振る (残り {st.session_state.rolls_left}回)"):
            for i in range(5):
                if not st.session_state.keeps[i]:
                    st.session_state.my_dice[i] = random.randint(1, 6)
            st.session_state.rolls_left -= 1
            st.rerun()
    
    # 攻撃（確定）ボタン
    if col_b.button("この役で攻撃！"):
        dmg, yakuname = calculate_damage(st.session_state.my_dice)
        st.write(f"### {yakuname}")
        
        new_hp1 = data["hp1"] - (dmg if my_id == "P2" else 0)
        new_hp2 = data["hp2"] - (dmg if my_id == "P1" else 0)
        
        update_game({
            "hp1": max(0, new_hp1),
            "hp2": max(0, new_hp2),
            "turn": enemy_id
        })
        # 初期化
        st.session_state.rolls_left = 3
        st.session_state.keeps = [False] * 5
        st.rerun()

else:
    st.info("相手がダイスを振っています...")
    time.sleep(3) # 3秒おきにデータベースを確認
    st.rerun()
