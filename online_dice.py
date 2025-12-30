import streamlit as st
from supabase import create_client
import time
import random

# --- 1. Supabase 接続 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. 判定ロジック (tttt.py 完全再現) ---
def check_pair(d): return any(d.count(x) >= 2 for x in set(d)) #
def check_three(d): return any(d.count(x) >= 3 for x in set(d)) #
def check_straight(d): 
    s = sorted(list(set(d)))
    return any(s[i:i+5] == list(range(s[i], s[i]+5)) for i in range(len(s)-4)) #
def check_full_house(d): 
    counts = [d.count(x) for x in set(d)]
    return 3 in counts and 2 in counts #
def check_yahtzee(d): return len(set(d)) == 1 #

class Card:
    def __init__(self, name, ctype, power, condition_func, cond_text, rarity, status_effect=None):
        self.name = name
        self.type = ctype
        self.power = power
        self.condition_func = condition_func
        self.cond_text = cond_text # 「ペア」などの表示用
        self.rarity = rarity
        self.status_effect = status_effect

# カードDB構築 (tttt.py の構成に基づく)
CARD_DB = {
    "ジェミニ・ダガー": Card("ジェミニ・ダガー", "attack", 15, check_pair, "ペア", "弱"),
    "トライ・ブラスト": Card("トライ・ブラスト", "attack", 25, check_three, "スリーカード", "中"),
    "崩壊の紫煙(毒)": Card("崩壊の紫煙(毒)", "status", 0, check_three, "スリーカード", "中", ("poison", 3)),
    "天階の連撃": Card("天階の連撃", "attack", 40, check_straight, "ストレート", "強"),
    "煉獄の業火(炎)": Card("煉獄の業火(炎)", "status", 0, check_straight, "ストレート", "強", ("burn", 2)),
    "慈悲の祝福": Card("慈悲の祝福", "heal", 30, check_pair, "ペア", "レア"),
    "終焉の聖家": Card("終焉の聖家", "attack", 60, check_full_house, "フルハウス", "レア")
}

INNATE_CARDS = [
    Card("固有:トリニティ", "attack", 20, check_three, "スリーカード", "固有"),
    Card("固有:五連光破斬", "attack", 25, check_straight, "ストレート", "固有"),
    Card("固有:神罰の五連星", "attack", 50, check_yahtzee, "ヤッツィー", "固有")
]

# --- 3. データベース同期 ---
def get_data(): return supabase.table("game_state").select("*").eq("id", 1).execute().data[0]
def update_db(u): supabase.table("game_state").update(u).eq("id", 1).execute()
def create_deck():
    d = (["ジェミニ・ダガー"]*20 + ["トライ・ブラスト"]*16 + ["崩壊の紫煙(毒)"]*2 + ["天階の連撃"]*10 + ["煉獄の業火(炎)"]*2 + ["慈悲の祝福"]*5 + ["終焉の聖家"]*5)
    random.shuffle(d)
    return d

# --- 4. UIデザイン (CSS) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .hp-val { font-size: 42px; font-weight: bold; color: #00FFAA; text-shadow: 0 0 10px #00FFAA; }
    .dice-container { display: flex; justify-content: space-around; background: #1A1C23; padding: 20px; border-radius: 15px; border: 1px solid #333; margin: 20px 0; }
    .dice-num { font-size: 48px; font-weight: bold; color: #00FFFF; text-shadow: 0 0 15px #00FFFF; }
    .card-panel { background: #262730; border-radius: 10px; padding: 15px; border-left: 5px solid #FF4B4B; margin-bottom: 10px; }
    .cond-tag { background: #444; color: #EEE; padding: 2px 8px; border-radius: 5px; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# --- 5. メインロジック ---
data = get_data()
role = st.sidebar.radio("役割選択", ["Player 1", "Player 2"])
me = "p1" if role == "Player 1" else "p2"
opp = "p2" if role == "Player 1" else "p1"
my_turn_id = "P1" if role == "Player 1" else "P2"

st.markdown("# ⚔️ YAHTZEE TACTICS")

# ステータス表示
c1, c2 = st.columns(2)
for i, p_key in enumerate(["p1", "p2"]):
    with (c1 if i == 0 else c2):
        st.markdown(f"### PLAYER {i+1} " + ("🔥" if i==0 else "❄️"))
        hp = data[f"hp{i+1}"]
        st.markdown(f"<span class='hp-val'>{hp} / 100</span>", unsafe_allow_html=True)
        st.progress(max(0, hp)/100)

st.divider()

if data["turn"] == my_turn_id:
    st.success("あなたのターンです")
    
    if "dice" not in st.session_state: st.session_state.dice = [1,1,1,1,1]
    if "phase" not in st.session_state: st.session_state.phase = "action"

    # 運命の刻印 (ダイス)
    st.write("### 🎲 運命の刻印")
    d_cols = st.columns(5)
    for i in range(5):
        d_cols[i].markdown(f"<div class='dice-container'><span class='dice-num'>{st.session_state.dice[i]}</span></div>", unsafe_allow_html=True)

    if st.session_state.phase == "action":
        b1, b2 = st.columns(2)
        if b1.button("🎴 カードを引いて交代", use_container_width=True):
            deck = data["deck"]
            if deck:
                if "hand" not in st.session_state: st.session_state.hand = []
                st.session_state.hand.append(deck.pop())
                update_db({"deck": deck, "turn": "P2" if my_turn_id=="P1" else "P1", "turn_count": data["turn_count"]+1})
                st.rerun()
        if b2.button("⚔️ 攻撃フェーズへ", use_container_width=True):
            st.session_state.phase = "battle"
            st.rerun()

    elif st.session_state.phase == "battle":
        if st.button("🎲 振り直す", use_container_width=True):
            st.session_state.dice = [random.randint(1, 6) for _ in range(5)]
            st.rerun()

        # 使用可能カードの構築
        used = data.get(f"{me}_used_innate", [])
        pool = [c for c in INNATE_CARDS if c.name not in used]
        for h_name in st.session_state.get("hand", []): pool.append(CARD_DB[h_name])
        
        available = [c for c in pool if c.condition_func(st.session_state.dice)] #

        if not available:
            st.warning("役が揃っていません")
            if st.button("パスして交代"):
                update_db({"turn": "P2" if my_turn_id=="P1" else "P1", "turn_count": data["turn_count"]+1})
                st.session_state.phase = "action"
                st.rerun()
        else:
            # カード選択パネル
            for idx, card in enumerate(available):
                with st.container():
                    st.markdown(f"""
                    <div class='card-panel'>
                        <strong>{card.name}</strong> <span class='cond-tag'>条件: {card.cond_text}</span><br>
                        <small>威力: {card.power} / レアリティ: {card.rarity}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"発動: {card.name}", key=f"act_{idx}", use_container_width=True):
                        # バトル処理
                        bonus = data.get(f"{me}_bonus", 0)
                        updates = {"turn": "P2" if my_turn_id=="P1" else "P1", "turn_count": data["turn_count"]+1}
                        
                        if card.type == "attack": updates[f"hp{2 if me=='p1' else 1}"] = max(0, data[f"hp{2 if me=='p1' else 1}"] - (card.power + bonus))
                        elif card.type == "heal": updates[f"hp{1 if me=='p1' else 2}"] = min(100, data[f"hp{1 if me=='p1' else 2}"] + card.power)
                        elif card.type == "status": updates[f"{opp}_status"] = {card.status_effect[0]: card.status_effect[1]}

                        if "固有" in card.name:
                            used.append(card.name)
                            if len(used) == 3: updates[f"{me}_bonus"] = bonus + 10; updates[f"{me}_used_innate"] = []
                            else: updates[f"{me}_used_innate"] = used
                        else: st.session_state.hand.remove(card.name)

                        update_db(updates)
                        st.session_state.phase = "action"
                        st.rerun()

else:
    st.info("相手のターンです...")
    time.sleep(3)
    st.rerun()

# サイドバー
st.sidebar.title("🎴 あなたの手札")
for h in st.session_state.get("hand", []):
    st.sidebar.info(f"{h}\n({CARD_DB[h].cond_text})")

if st.sidebar.button("♻️ ゲームリセット"):
    update_db({"hp1": 100, "hp2": 100, "turn": "P1", "turn_count": 0, "p1_status": {}, "p2_status": {}, "p1_bonus": 0, "p2_bonus": 0, "p1_used_innate": [], "p2_used_innate": [], "deck": create_deck()})
    st.session_state.hand = []
    st.rerun()
