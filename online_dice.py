import streamlit as st
from supabase import create_client
import time
import random

# --- 1. Supabase 接続 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. 判定ロジック & クラス (tttt.py準拠) ---
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
    def __init__(self, name, ctype, power, condition, rarity, status_effect=None):
        self.name, self.type, self.power, self.condition, self.rarity, self.status_effect = name, ctype, power, condition, rarity, status_effect

# カードDB
CARD_DB = {
    "ジェミニ・ダガー": Card("ジェミニ・ダガー", "attack", 15, check_pair, "弱"),
    "トライ・ブラスト": Card("トライ・ブラスト", "attack", 25, check_three, "中"),
    "崩壊の紫煙(毒)": Card("崩壊の紫煙(毒)", "status", 0, check_three, "中", ("poison", 3)),
    "天階の連撃": Card("天階の連撃", "attack", 40, check_straight, "強"),
    "煉獄の業火(炎)": Card("煉獄の業火(炎)", "status", 0, check_straight, "強", ("burn", 2)),
    "慈悲の祝福": Card("慈悲 de 祝福", "heal", 30, check_pair, "レア"),
    "終焉の聖家": Card("終焉の聖家", "attack", 60, check_full_house, "レア")
}

INNATE_CARDS = [
    Card("固有:トリニティ", "attack", 20, check_three, "固有"),
    Card("固有:五連光破斬", "attack", 25, check_straight, "固有"),
    Card("固有:神罰の五連星", "attack", 50, check_yahtzee, "固有")
]

# --- 3. データベース同期 ---
def get_data(): return supabase.table("game_state").select("*").eq("id", 1).execute().data[0]
def update_db(u): supabase.table("game_state").update(u).eq("id", 1).execute()
def create_deck():
    d = (["ジェミニ・ダガー"]*20 + ["トライ・ブラスト"]*16 + ["崩壊の紫煙(毒)"]*2 + ["天階の連撃"]*10 + ["煉獄の業火(炎)"]*2 + ["慈悲の祝福"]*5 + ["終焉の聖家"]*5)
    random.shuffle(d)
    return d

# --- 4. スタイル設定 (CSS) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    .hp-text { font-size: 36px; font-weight: bold; color: #00FFAA; }
    .dice-box { background: rgba(0, 255, 255, 0.1); border: 2px solid #00FFFF; border-radius: 10px; padding: 20px; text-align: center; font-size: 40px; margin: 10px; box-shadow: 0 0 15px #00FFFF; }
    .action-btn { width: 100%; border-radius: 20px; }
</style>
""", unsafe_allow_html=True)

# --- 5. メインUI ---
data = get_data()
role = st.sidebar.radio("ROLE SELECT", ["Player 1", "Player 2"])
me = "p1" if role == "Player 1" else "p2"
opp = "p2" if role == "Player 1" else "p1"
my_turn = "P1" if role == "Player 1" else "P2"

st.title("⚔️ YAHTZEE TACTICS ⚔️")

# HP表示エリア
c1, c2 = st.columns(2)
for i, p in enumerate(["p1", "p2"]):
    with (c1 if i == 0 else c2):
        st.markdown(f"### PLAYER {i+1} 🔥" if i==0 else f"### PLAYER {i+1}")
        hp = data[f"hp{i+1}"]
        st.markdown(f"<p class='hp-text'>{hp} / 100</p>", unsafe_allow_html=True)
        st.progress(max(0, hp)/100)
        st.write(f"⚔️ Bonus: +{data.get(f'{p}_bonus', 0)}")

st.divider()

# --- ターン処理 ---
if data["turn"] == my_turn:
    # 状態異常ダメ
    if st.session_state.get("processed") != data["turn_count"]:
        my_st = data.get(f"{me}_status", {})
        curr_hp = data[f"hp{1 if me=='p1' else 2}"]
        for s, t in my_st.items():
            if t > 0:
                curr_hp -= (5 if s=="poison" else 10)
                my_st[s] -= 1
        update_db({f"hp{1 if me=='p1' else 2}": max(0, curr_hp), f"{me}_status": my_st})
        st.session_state["processed"] = data["turn_count"]
        st.rerun()

    # フェーズ管理
    if "phase" not in st.session_state: st.session_state.phase = "action"
    if "dice" not in st.session_state: st.session_state.dice = [random.randint(1,6) for _ in range(5)]

    # 運命の刻印 (ダイス表示)
    st.write("### 🎲 運命の刻印")
    d_cols = st.columns(5)
    for i in range(5):
        d_cols[i].markdown(f"<div class='dice-box'>{st.session_state.dice[i]}</div>", unsafe_allow_html=True)

    if st.session_state.phase == "action":
        st.divider()
        bt1, bt2 = st.columns(2)
        if bt1.button("🎴 カードを引いて交代", use_container_width=True):
            deck = data["deck"]
            if deck:
                if "hand" not in st.session_state: st.session_state.hand = []
                st.session_state.hand.append(deck.pop())
                update_db({"deck": deck, "turn": "P2" if my_turn=="P1" else "P1", "turn_count": data["turn_count"]+1})
                st.rerun()
        if bt2.button("⚔️ 攻撃フェーズへ", use_container_width=True):
            st.session_state.phase = "battle"
            st.rerun()

    elif st.session_state.phase == "battle":
        if st.button("🎲 振り直す", use_container_width=True):
            st.session_state.dice = [random.randint(1,6) for _ in range(5)]
            st.rerun()
        
        # 使用可能カード
        used = data.get(f"{me}_used_innate", [])
        pool = [c for c in INNATE_CARDS if c.name not in used]
        for cn in st.session_state.get("hand", []): pool.append(CARD_DB[cn])
        
        available = [c for c in pool if c.condition(st.session_state.dice)]
        
        if not available:
            st.error("役がありません")
            if st.button("パスして交代"):
                update_db({"turn": "P2" if my_turn=="P1" else "P1", "turn_count": data["turn_count"]+1})
                st.session_state.phase = "action"
                st.rerun()
        else:
            # カードを横並びで表示
            idx = 0
            for i in range((len(available)+2)//3):
                cols = st.columns(3)
                for j in range(3):
                    if idx < len(available):
                        c = available[idx]
                        with cols[j]:
                            st.write(f"**{c.name}**")
                            st.caption(f"威力:{c.power} / 役:{c.rarity}")
                            if st.button("発動", key=f"btn_{idx}", use_container_width=True):
                                # バトルロジック
                                bonus = data.get(f"{me}_bonus", 0)
                                up = {"turn": "P2" if my_turn=="P1" else "P1", "turn_count": data["turn_count"]+1}
                                if c.type == "attack": up[f"hp{2 if me=='p1' else 1}"] = max(0, data[f"hp{2 if me=='p1' else 1}"] - (c.power + bonus))
                                elif c.type == "heal": up[f"hp{1 if me=='p1' else 2}"] = min(100, data[f"hp{1 if me=='p1' else 2}"] + c.power)
                                elif c.type == "status": up[f"{opp}_status"] = {c.status_effect[0]: c.status_effect[1]}
                                
                                if "固有" in c.name:
                                    used.append(c.name)
                                    if len(used) == 3: up[f"{me}_bonus"] = bonus + 10; up[f"{me}_used_innate"] = []
                                    else: up[f"{me}_used_innate"] = used
                                else: st.session_state.hand.remove(c.name)
                                
                                update_db(up)
                                st.session_state.phase = "action"
                                st.rerun()
                        idx += 1

else:
    st.info("相手の行動を同期中...")
    time.sleep(3)
    st.rerun()

# --- 6. サイドバー手札 ---
st.sidebar.title("🎴 あなたの手札")
for h in st.session_state.get("hand", []):
    st.sidebar.markdown(f"**🔹 {h}**")

if st.sidebar.button("♻️ ゲームをリセット"):
    update_db({"hp1": 100, "hp2": 100, "turn": "P1", "turn_count": 0, "p1_status": {}, "p2_status": {}, "p1_bonus": 0, "p2_bonus": 0, "p1_used_innate": [], "p2_used_innate": [], "deck": create_deck()})
    st.session_state.hand = []
    st.rerun()
