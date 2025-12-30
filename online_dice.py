import streamlit as st
from supabase import create_client
import time
import random
import streamlit.components.v1 as components

MAX_HP = 100

# 効果音再生用関数
def play_se(url):
    components.html(
        f"""
        <script>
            var audio = new Audio("{url}");
            audio.volume = 0.6;
            audio.play();
        </script>
        """,
        height=0,
    )

SE_URL = "https://github.com/taigamatumoto37/dice-game/raw/5c9c1c88d3d308d48494ed197ece6eb88a5ea8d3/%E6%B1%BA%E5%AE%9A%E3%83%9C%E3%82%BF%E3%83%B3%E3%82%92%E6%8A%BC%E3%81%998.mp3"
bgm_url = "https://github.com/taigamatumoto37/dice-game/raw/main/001_%E3%80%90%E7%9D%A1%E7%9C%A030%E5%88%86%E5%89%8D%E7%94%A8%E3%80%91%E7%86%9F%E7%9D%A1%E3%81%A7%E3%81%8D%E3%82%8B%E7%9D%A1%E7%9C%A0%E7%94%A8BGM%20Smooth%20Jazz%E3%80%90%E5%BA%83%E5%91%8A%E3%81%AA%E3%81%97%E3%80%91Deep%20Sleep%2C%20Relaxing%2C%20Healing%2C%20Sleep%20Music%2C%2030%20miniutes.mp3"

components.html(
    f"""
    <audio id="bgm" src="{bgm_url}" loop></audio>
    <script>
        window.parent.document.body.addEventListener('click', function() {{
            var audio = document.getElementById('bgm');
            if (audio.paused) {{
                audio.play().catch(e => console.log("BGM Playback failed:", e));
            }}
        }}, {{ once: true }});
    </script>
    """,
    height=0,
)

# --- 1. Supabase 接続 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. カード定義 ---
class Card:
    def __init__(self, name, ctype, power, condition_func, cond_text):
        self.name, self.type, self.power, self.condition_func, self.cond_text = name, ctype, power, condition_func, cond_text

def check_pair(d): return any(d.count(x) >= 2 for x in set(d))
def check_three(d): return any(d.count(x) >= 3 for x in set(d))
def check_straight(d): 
    s = sorted(list(set(d)))
    return any(s[i:i+5] == list(range(s[i], s[i]+5)) for i in range(len(s)-4))
def check_yahtzee(d): return len(set(d)) == 1

CARD_DB = {
    "ジェミニ・ダガー": Card("ジェミニ・ダガー", "attack", 12, check_pair, "ペア"),
    "トライ・ブラスト": Card("トライ・ブラスト", "attack", 20, check_three, "スリーカード"),
    "クアッド・ボルテックス": Card("クアッド・ボルテックス", "attack", 35, lambda d: any(d.count(x) >= 4 for x in set(d)), "フォーカード"),
    "五行封印斬": Card("五行封印斬", "attack", 60, check_yahtzee, "ヤッツィー"),
    "スモール・エッジ": Card("スモール・エッジ", "attack", 25, lambda d: len(set(d)) >= 3, "3種類以上の出目"),
    "スカイ・ストライク": Card("スカイ・ストライク", "attack", 35, lambda d: len(set(d)) >= 4, "4種類以上の出目"),
    "慈悲 of 祝福": Card("慈悲 of 祝福", "heal", 20, check_pair, "ペア"),
    "聖なる祈り": Card("聖なる祈り", "heal", 30, lambda d: any(x in d for x in [1, 6]), "1か6がある"),
    "生命の輝き": Card("生命の輝き", "heal", 45, check_three, "スリーカード"),
    "再生の福音": Card("再生の福音", "heal", 80, check_yahtzee, "ヤッツィー"),
    "フルハウス・バスター": Card("フルハウス・バスター", "attack", 40, lambda d: len(set(d)) <= 3, "出目が3種類以下"),
    "偶数の審判": Card("偶数の審判", "attack", 30, lambda d: any(x % 2 == 0 for x in d), "偶数が1つでもある"),
    "奇数の洗礼": Card("奇数の洗礼", "attack", 30, lambda d: any(x % 2 != 0 for x in d), "奇数が1つでもある"),
    "ハイ・ローラー": Card("ハイ・ローラー", "attack", 35, lambda d: sum(d) >= 18, "合計18以上"),
    "ロー・ローラー": Card("ロー・ローラー", "attack", 35, lambda d: sum(d) <= 15, "合計15以下"),
    "プチ・ヒール": Card("プチ・ヒール", "heal", 10, lambda d: True, "無条件"),
    "光の防壁": Card("光の防壁", "heal", 35, lambda d: check_pair(d), "ペア"),
    "アイアン・ウォール": Card("アイアン・ウォール", "guard", 15, lambda d: True, "無条件"),
    "マジック・ミラー": Card("マジック・ミラー", "guard", 30, lambda d: True, "無条件"),
}

INNATE_DECK = [
    Card("固有:トリニティ", "attack", 20, check_three, "スリーカード"),
    Card("固有:五連光破斬", "attack", 30, check_straight, "ストレート"),
    Card("固有:神罰 of 五連星", "attack", 50, check_yahtzee, "ヤッツィー"),
    Card("固有:双撃の構え", "attack", 15, check_pair, "ペア"),
    Card("固有:生命の共鳴", "heal", 25, lambda d: len(set([x for x in d if d.count(x) >= 2])) >= 2, "2ペア"),
    Card("固有:等位の福音", "heal", 40, lambda d: len(set(d)) == 2 and any(d.count(x) == 3 for x in set(d)), "フルハウス"),
    Card("固有:轟力・大山波", "attack", 35, lambda d: sum(d) >= 22, "合計22以上"),
    Card("固有:静寂・小波斬", "attack", 25, lambda d: sum(d) <= 12, "合計12以下"),
]

def get_data(): return supabase.table("game_state").select("*").eq("id", 1).execute().data[0]
def update_db(u): 
    try: supabase.table("game_state").update(u).eq("id", 1).execute()
    except: pass

# --- 3. CSS ---
st.markdown("""
<style>
    .innate-card { border: 2px solid #FFD700 !important; background: linear-gradient(145deg, #1A1C23, #2A2D35) !important; box-shadow: 0 0 15px rgba(255, 215, 0, 0.4); }
    .stApp { background-color: #0E1117; color: white; }
    .hp-bar-container { background: #333; height: 10px; border-radius: 5px; margin-top: 5px; }
    .hp-bar-fill { background: #00FFAA; height: 100%; border-radius: 5px; transition: width 0.5s; }
    .dice-slot { background: rgba(0, 0, 0, 0.5); border: 2px solid #00FFFF; border-radius: 10px; height: 80px; display: flex; align-items: center; justify-content: center; font-size: 35px; color: #00FFFF; }
    .opp-dice { border-color: #FF4B4B; color: #FF4B4B; height: 50px; font-size: 20px; opacity: 0.7; }
    div.stButton > button { background-color: #FF5555 !important; color: white !important; width: 100% !important; border-radius: 5px !important; font-weight: bold !important; }
    .skill-card { border: 1px solid #FF5555; border-radius: 10px; padding: 15px; background: #1A1C23; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 4. メイン処理 ---
data = get_data()
role = st.sidebar.radio("役割を選択", ["Player 1", "Player 2"])
me, opp, my_id, opp_id = ("p1", "p2", 1, 2) if role == "Player 1" else ("p2", "p1", 2, 1)

st.title("⚔️ YAHTZEE TACTICS ⚔️")

# --- HP表示エリア ---
c1, c2 = st.columns(2)
for p_num in [1, 2]:
    with (c1 if p_num == 1 else c2):
        hp = data[f"hp{p_num}"]
        st.write(f"### PLAYER {p_num} {'🔥' if data['turn'] == f'P{p_num}' else ''}")
        st.markdown(f"**❤️ HP: `{hp}` / {MAX_HP}**")
        hp_percent = max(0, min(100, (hp / MAX_HP) * 100)) 
        st.markdown(f"<div class='hp-bar-container'><div class='hp-bar-fill' style='width:{hp_percent}%'></div></div>", unsafe_allow_html=True)

# --- 相手のダイス表示 ---
st.write(f"### 🛡️ 相手(P{opp_id})の刻印")
o_dice = data.get(f"{opp}_dice", [1,1,1,1,1])
oc = st.columns(5)
for i in range(5):
    oc[i].markdown(f"<div class='dice-slot opp-dice'>{o_dice[i]}</div>", unsafe_allow_html=True)

st.divider()

# --- 重要：変数の定義を防御ロジックより先に行う ---
is_my_turn = (data["turn"] == f"P{my_id}")
current_phase = data.get("phase", "ATK")
pending_dmg = data.get("pending_damage", 0)

# --- 防御側の処理：相手が攻撃してきたとき ---
if not is_my_turn and current_phase == "DEF":
    st.warning(f"⚠️ 相手の攻撃！ **{pending_dmg}** ダメージが来ます！")
    my_hand_names = data.get(f"{me}_hand", [])
    guards = [CARD_DB[name] for name in my_hand_names if name in CARD_DB and CARD_DB[name].type == "guard"]
    
    cols = st.columns(len(guards) + 1 if guards else 1)
    for i, g_card in enumerate(guards):
        with cols[i]:
            if st.button(f"🛡️ {g_card.name}\n(軽減: {g_card.power})", key=f"guard_{i}"):
                final_dmg = max(0, pending_dmg - g_card.power)
                new_hand = [n for n in my_hand_names if n != g_card.name]
                update_db({
                    f"hp{my_id}": data[f"hp{my_id}"] - final_dmg,
                    f"{me}_hand": new_hand,
                    "pending_damage": 0, "phase": "ATK",
                    "turn": f"P{my_id}", "turn_count": data["turn_count"] + 1
                })
                st.rerun()
    with cols[-1]:
        if st.button("そのまま受ける", type="primary"):
            update_db({
                f"hp{my_id}": data[f"hp{my_id}"] - pending_dmg,
                "pending_damage": 0, "phase": "ATK",
                "turn": f"P{my_id}", "turn_count": data["turn_count"] + 1
            })
            st.rerun()
    st.stop()

# --- 攻撃側の待機表示 ---
if is_my_turn and current_phase == "DEF":
    st.info("⌛ 相手の防御選択を待っています...")
    time.sleep(2)
    st.rerun()

# --- ダイスロール処理 ---
if is_my_turn:
    if st.session_state.get("last_processed_turn") != data["turn_count"]:
        st.session_state.dice = [random.randint(1, 6) for _ in range(5)]
        st.session_state.rolls = 2
        st.session_state.keep = [False] * 5
        st.session_state.last_processed_turn = data["turn_count"]
        update_db({f"{me}_dice": st.session_state.dice})
        st.rerun()

    st.write(f"### 🎲 あなたの刻印 (残りリロール回数: {st.session_state.get('rolls', 0)})")
    cols = st.columns(5)
    for i in range(5):
        st.session_state.keep[i] = st.checkbox(f"Keep", key=f"keep_{i}_{data['turn_count']}", value=st.session_state.get("keep", [False]*5)[i])
        cols[i].markdown(f"<div class='dice-slot'>{st.session_state.dice[i]}</div>", unsafe_allow_html=True)
    
    if st.session_state.rolls > 0:
        if st.button("🎲 ダイスを振る"):
            st.session_state.dice = [v if st.session_state.keep[i] else random.randint(1, 6) for i, v in enumerate(st.session_state.dice)]
            st.session_state.rolls -= 1
            update_db({f"{me}_dice": st.session_state.dice})
            st.rerun()

# --- スキル表示 ---
st.write(f"### ⚔️ PLAYER {my_id} のスキル")
my_hand_from_db = list(data.get(f"{me}_hand", []))
my_used_innate = list(data.get(f"{me}_used_innate", []))
pool = [c for c in INNATE_DECK if c.name not in my_used_innate]
for h_name in my_hand_from_db:
    if h_name in CARD_DB: pool.append(CARD_DB[h_name])

sc = st.columns(3)
for idx, card in enumerate(pool):
    is_ready = card.condition_func(st.session_state.dice) if (is_my_turn and any(st.session_state.dice)) else False
    is_innate = "固有" in card.name
    type_color = "#FF5555" if card.type == "attack" else ("#00FFAA" if card.type == "heal" else "#5555FF")
    
    with sc[idx % 3]:
        st.markdown(f"<div class='skill-card' style='border-color: {type_color if is_ready else '#555555'};'><b>{card.name}</b><br><small>{card.power} | {card.cond_text}</small></div>", unsafe_allow_html=True)
        if is_my_turn and is_ready and card.type != "guard":
            if st.button("発動", key=f"atk_{idx}"):
                play_se(SE_URL)
                upd = {}
                if card.type == "attack":
                    upd["pending_damage"], upd["phase"] = card.power, "DEF"
                else:
                    upd[f"hp{my_id}"] = data[f"hp{my_id}"] + card.power
                    upd["turn"], upd["turn_count"] = f"P{opp_id}", data["turn_count"] + 1
                
                if is_innate: upd[f"{me}_used_innate"] = my_used_innate + [card.name]
                else: upd[f"{me}_hand"] = [n for n in my_hand_from_db if n != card.name]
                update_db(upd); st.rerun()

if is_my_turn and st.button("ターンを終了してドロー"):
    latest = get_data()
    deck = latest.get("deck", [])
    hand = list(latest.get(f"{me}_hand", []))
    if deck: hand.append(deck.pop(0))
    update_db({"deck": deck, f"{me}_hand": hand, "turn": f"P{opp_id}", "turn_count": latest["turn_count"] + 1})
    st.rerun()

with st.sidebar:
    if st.button("🚨 全リセット"):
        all_cards = list(CARD_DB.keys()); new_deck = all_cards * 2; random.shuffle(new_deck)
        update_db({"hp1": 100, "hp2": 100, "p1_hand": [], "p2_hand": [], "p1_used_innate": [], "p2_used_innate": [], "turn": "P1", "turn_count": 0, "pending_damage": 0, "phase": "ATK", "deck": new_deck})
        st.rerun()
