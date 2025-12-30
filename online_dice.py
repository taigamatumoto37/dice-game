import streamlit as st
from supabase import create_client
import time
import random

# --- 1. Supabase 接続 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. カード定義（説明文を追加） ---
class Card:
    def __init__(self, name, ctype, power, condition_func, cond_text, desc, effect_type=None, duration=0):
        self.name, self.type, self.power, self.condition_func, self.cond_text = name, ctype, power, condition_func, cond_text
        self.desc = desc # 効果の説明文
        self.effect_type, self.duration = effect_type, duration

def check_pair(d): return any(d.count(x) >= 2 for x in set(d))
def check_three(d): return any(d.count(x) >= 3 for x in set(d))
def check_straight(d): 
    s = sorted(list(set(d)))
    return any(s[i:i+5] == list(range(s[i], s[i]+5)) for i in range(len(s)-4))
def check_full_house(d): 
    counts = [d.count(x) for x in set(d)]
    return 3 in counts and 2 in counts

# 効果説明をカードDBに統合
CARD_DB = {
    "ジェミニ・ダガー": Card("ジェミニ・ダガー", "attack", 15, check_pair, "ペア", "双子の短剣による素早い二連撃。"),
    "トライ・ブラスト": Card("トライ・ブラスト", "attack", 25, check_three, "スリーカード", "三位一体の魔力による爆発攻撃。"),
    "慈悲の祝福": Card("慈悲の祝福", "heal", 35, check_pair, "ペア", "聖なる光が負傷を癒やす。HP上限を超えて回復可能。"),
    "崩壊の紫煙": Card("崩壊の紫煙", "status", 5, check_three, "スリーカード", "毒を帯びた煙。3ターンの間、毎ターン5ダメージを与える。", "poison", 3),
    "煉獄の業火": Card("煉獄の業火", "status", 10, check_straight, "ストレート", "消えない炎。2ターンの間、毎ターン10ダメージを与える。", "burn", 2),
    "天階の連撃": Card("天階の連撃", "attack", 45, check_straight, "ストレート", "空を駆けるような怒涛の連続攻撃。"),
    "終焉 of 聖家": Card("終焉 of 聖家", "attack", 65, check_full_house, "フルハウス", "全てを無に帰す聖なる一撃。")
}

def get_data(): return supabase.table("game_state").select("*").eq("id", 1).execute().data[0]
def update_db(u): supabase.table("game_state").update(u).eq("id", 1).execute()

# --- 3. UIデザイン ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    div.stButton > button { background-color: #FF4B4B !important; color: white !important; font-weight: bold !important; border-radius: 10px !important; border: none !important; transition: 0.3s; }
    div.stButton > button:hover { background-color: #FF2B2B !important; transform: scale(1.02); }
    .hp-text { font-size: 38px; font-weight: bold; color: #00FFAA; text-shadow: 0 0 15px #00FFAA66; }
    
    /* カード詳細パネル */
    .card-panel { background: #1E1E26; padding: 15px; border-radius: 12px; border-left: 5px solid #FF4B4B; margin-bottom: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
    .card-title { font-size: 1.2em; font-weight: bold; color: #FFFFFF; }
    .card-effect { font-size: 1.1em; color: #FF4B4B; font-weight: bold; margin-top: 5px; }
    .card-desc { font-size: 0.9em; color: #AAAAAA; font-style: italic; margin-top: 8px; line-height: 1.4; }
    .card-cond { display: inline-block; background: #333; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; color: #DDD; margin-top: 5px; }
    
    .status-tag { padding: 4px 10px; border-radius: 6px; font-size: 13px; font-weight: bold; }
    .poison { background: #8A2BE2; } .burn { background: #FF4500; }
</style>
""", unsafe_allow_html=True)

# --- 4. メインロジック ---
data = get_data()

# 終了判定
if data["hp1"] <= 0 or data["hp2"] <= 0:
    st.markdown(f"<h1 style='text-align:center;'>🏆 {'Player 1' if data['hp2'] <= 0 else 'Player 2'} VICTORY</h1>", unsafe_allow_html=True)
    if st.button("♻️ ゲームをフルリセット"):
        update_db({"hp1": 100, "hp2": 100, "turn": "P1", "turn_count": 0, "p1_status": None, "p2_status": None})
        st.rerun()
    st.stop()

role = st.sidebar.radio("役割", ["Player 1", "Player 2"])
me, opp, my_id, opp_id = ("p1", "p2", 1, 2) if role == "Player 1" else ("p2", "p1", 2, 1)

st.title("⚔️ YAHTZEE TACTICS")

# HP & 状態表示
c1, c2 = st.columns(2)
for i, p_prefix in enumerate(["p1", "p2"]):
    with (c1 if i == 0 else c2):
        st.write(f"**PLAYER {i+1}**")
        hp = data[f"hp{i+1}"]
        st.markdown(f"<p class='hp-text'>{hp}</p>", unsafe_allow_html=True)
        st.progress(min(1.0, max(0, hp) / 100))
        s = data.get(f"{p_prefix}_status")
        if s: st.markdown(f"<span class='status-tag {s['type']}'>{s['type'].upper()} 残り:{s['dur']}回</span>", unsafe_allow_html=True)

st.divider()

if data["turn"] == (f"P{my_id}"):
    # ターン開始処理
    if st.session_state.get("last_t_count") != data["turn_count"]:
        updates = {"turn_count": data["turn_count"]}
        current_hp = data[f"hp{my_id}"]
        s = data.get(f"{me}_status")
        if s and s['dur'] > 0:
            current_hp -= s['pow']
            new_dur = s['dur'] - 1
            updates[f"{me}_status"] = {"type": s['type'], "pow": s['pow'], "dur": new_dur} if new_dur > 0 else None
            updates[f"hp{my_id}"] = current_hp
            update_db(updates)
            st.warning(f"状態異常ダメージ発生: {s['pow']} DMG")
            time.sleep(1); st.rerun()

        st.session_state.dice = [random.randint(1, 6) for _ in range(5)]
        st.session_state.rolls_left = 2
        st.session_state.keep = [False] * 5
        st.session_state["last_t_count"] = data["turn_count"]
        st.rerun()

    # --- ダイスエリア ---
    st.write(f"🎲 振り直し可能: **{st.session_state.rolls_left}** 回")
    d_cols = st.columns(5)
    for i in range(5):
        with d_cols[i]:
            st.markdown(f"<div style='background:#1A1C23; padding:15px; text-align:center; font-size:30px; border-radius:10px; border:1px solid #444; color:#00FFFF;'>{st.session_state.dice[i]}</div>", unsafe_allow_html=True)
            st.session_state.keep[i] = st.checkbox("Keep", key=f"k{i}")

    # --- 技の表示（効果説明付き） ---
    hand = st.session_state.get("hand", [])
    pool = [CARD_DB[h] for h in hand if h in CARD_DB]
    available = [c for c in pool if c.condition_func(st.session_state.dice)]

    st.write("### ⚔️ 発動可能なアクション")
    if available:
        for idx, card in enumerate(available):
            # 効果内容のテキスト生成
            if card.type == "attack": effect_val = f"相手に {card.power} ダメージ"
            elif card.type == "heal": effect_val = f"自分のHPを {card.power} 回復 (上限なし)"
            else: effect_val = f"相手に {card.effect_type} 状態を付与 ({card.power}DMG × {card.duration}T)"

            # パネル表示
            st.markdown(f"""
                <div class='card-panel'>
                    <div class='card-title'>{card.name}</div>
                    <div class='card-cond'>発動条件: {card.cond_text}</div>
                    <div class='card-effect'>▶ {effect_val}</div>
                    <div class='card-desc'>{card.desc}</div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"発動：{card.name}", key=f"btn_{idx}"):
                latest = get_data()
                updates = {"turn": f"P{opp_id}", "turn_count": latest["turn_count"] + 1}
                if card.type == "attack": updates[f"hp{opp_id}"] = latest[f"hp{opp_id}"] - card.power
                elif card.type == "heal": updates[f"hp{my_id}"] = latest[f"hp{my_id}"] + card.power
                elif card.type == "status": updates[f"{opp}_status"] = {"type": card.effect_type, "pow": card.power, "dur": card.duration}
                
                hand.remove(card.name); st.session_state.hand = hand
                update_db(updates); st.rerun()
    else:
        st.info("条件を満たしているカードがありません。振り直すか、カードを引いてください。")

    # --- 共通ボタン ---
    st.divider()
    col_x, col_y = st.columns(2)
    with col_x:
        if st.session_state.rolls_left > 0 and st.button("🎲 選択以外を振り直す"):
            for i in range(5):
                if not st.session_state.keep[i]: st.session_state.dice[i] = random.randint(1, 6)
            st.session_state.rolls_left -= 1; st.rerun()
    with col_y:
        if len(hand) < 5 and st.button("🎴 確定してカードを引く"):
            deck = data["deck"]
            if deck:
                hand.append(deck.pop()); st.session_state.hand = hand
                update_db({"deck": deck, "turn": f"P{opp_id}", "turn_count": data["turn_count"]+1})
                st.rerun()
else:
    st.info("相手がターンを進行中です...")
    time.sleep(3); st.rerun()

st.sidebar.write("### あなたの手札")
for h in st.session_state.get("hand", []): st.sidebar.info(h)
