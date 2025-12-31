import streamlit as st
from supabase import create_client
import time
import random
import streamlit.components.v1 as components



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
DICE_ROLL_SE = "https://github.com/taigamatumoto37/dice-game/raw/5c9c1c88d3d308d48494ed197ece6eb88a5ea8d3/%E6%B1%BA%E5%AE%9A%E3%83%9C%E3%82%BF%E3%83%B3%E3%82%92%E6%8A%BC%E3%81%998.mp3"
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
    "女神の休息": Card("女神の休息", "heal", 15, lambda d: True, "無条件"), # 追加
    "癒しの波動": Card("癒しの波動", "heal", 25, check_pair, "ペア"), # 追加
    "エナジー・ドレイン": Card("エナジー・ドレイン", "heal", 45, lambda d: sum(d) >= 20, "合計20以上"), # 追加
    "ナイト・シールド": Card("ナイト・シールド", "guard", 25, lambda d: True, "無条件"), # 追加
    "ホーリー・バリア": Card("ホーリー・バリア", "guard", 45, lambda d: True, "無条件"), # 追加
    "ミラー・シールド": Card("ミラー・シールド", "guard", 1.0, lambda d: True, "100%反射"),
    "トゲトゲの盾": Card("トゲトゲの盾", "guard", 0.5, lambda d: True, "50%反射+50%軽減"),
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
#CSS--------
st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at top, #0b0f1a 0%, #05070d 60%, #02030a 100%);
    color: #e6f1ff;
    font-family: "Segoe UI", "Hiragino Kaku Gothic ProN", sans-serif;
}

.innate-card {
    border: 2px solid transparent !important;
    background:
        linear-gradient(#0b1020, #0b1020) padding-box,
        linear-gradient(135deg, #ffd700, #ff8c00, #ffd700) border-box !important;
    border-radius: 14px;
    box-shadow: 0 0 25px rgba(255, 200, 0, 0.45);
}

.hp-bar-container {
    background: linear-gradient(180deg, #111, #1a1a1a);
    height: 12px;
    border-radius: 999px;
    margin-top: 6px;
    overflow: hidden;
}

.hp-bar-fill {
    background: linear-gradient(90deg, #00ffa6, #00c8ff, #7cff00);
    height: 100%;
    border-radius: 999px;
    transition: width 0.35s ease;
    filter: drop-shadow(0 0 6px rgba(0, 255, 200, 0.7));
}

.dice-slot {
    background: linear-gradient(145deg, rgba(10,15,35,0.9), rgba(0,0,0,0.9));
    border: 2px solid transparent;
    border-radius: 16px;
    height: 90px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 38px;
    font-weight: 900;
    color: #6cfaff;
    box-shadow:
        inset 0 0 12px rgba(0, 255, 255, 0.25),
        0 0 18px rgba(0, 255, 255, 0.45);
}

.opp-dice {
    background: rgba(40, 0, 0, 0.6);
    border-color: #ff3b3b;
    color: #ff6a6a;
    height: 54px;
    font-size: 22px;
    box-shadow: 0 0 10px rgba(255, 60, 60, 0.6);
}

.skill-card {
    border-radius: 16px;
    padding: 16px;
    background:
        linear-gradient(160deg, rgba(20,25,55,0.9), rgba(10,12,25,0.95));
    margin-bottom: 14px;
    box-shadow:
        0 10px 30px rgba(0,0,0,0.75),
        inset 0 0 10px rgba(120, 180, 255, 0.08);
}

div.stButton > button {
    background: linear-gradient(135deg, #ff3b3b, #ff7a18) !important;
    color: #ffffff !important;
    width: 100% !important;
    border-radius: 10px !important;
    font-weight: 900 !important;
    letter-spacing: 1px;
    border: none !important;
    box-shadow:
        0 6px 18px rgba(255, 80, 80, 0.7),
        inset 0 0 6px rgba(255,255,255,0.25);
}

div.stButton > button:hover {
    transform: scale(1.03);
    filter: brightness(1.15);
    box-shadow:
        0 10px 28px rgba(255, 100, 100, 0.95),
        inset 0 0 8px rgba(255,255,255,0.35);
}
@keyframes sparkle {
    0%   { box-shadow: 0 0 6px rgba(255,255,255,0.2), 0 0 12px rgba(0,200,255,0.2); }
    50%  { box-shadow: 0 0 14px rgba(255,255,255,0.9), 0 0 28px rgba(0,200,255,0.9); }
    100% { box-shadow: 0 0 6px rgba(255,255,255,0.2), 0 0 12px rgba(0,200,255,0.2); }
}

@keyframes shine {
    0% { background-position: 0% 50%; }
    100% { background-position: 200% 50%; }
}

.skill-card.active {
    position: relative;
    border: 2px solid transparent;
    background:
        linear-gradient(#0b1020, #0b1020) padding-box,
        linear-gradient(
            120deg,
            #00faff,
            #7cff00,
            #ffd700,
            #00faff
        ) border-box;
    background-size: 300% 300%;
    animation:
        sparkle 1.4s infinite ease-in-out,
        shine 2.5s linear infinite;
}

.skill-card.active::after {
    content: "";
    position: absolute;
    inset: -6px;
    border-radius: 20px;
    background: radial-gradient(circle, rgba(255,255,255,0.8) 0%, transparent 70%);
    opacity: 0.6;
    filter: blur(10px);
    pointer-events: none;
}
.skill-card.heal {
    border: 2px solid #00FF99;
    background:
        linear-gradient(#0b1020, #0b1020) padding-box,
        linear-gradient(120deg, #00FF99, #7CFFB2, #00FF99) border-box;
    background-size: 200% 200%;
}

.skill-card.heal.active {
    animation: healGlow 1.5s infinite ease-in-out;
}
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
        st.markdown(f"**❤️ HP: `{hp}`**")
        # HPが100を超えてもバーが壊れないように計算
        hp_percent = max(0, (hp / 100) * 100)
        st.markdown(f"<div class='hp-bar-container'><div class='hp-bar-fill' style='width:{min(100, hp_percent)}%'></div></div>", unsafe_allow_html=True)

# --- 勝敗判定エリア ---
p1_hp = data["hp1"]
p2_hp = data["hp2"]

if p1_hp <= 0 or p2_hp <= 0:
    winner = "Player 2" if p1_hp <= 0 else "Player 1"
    
    # 反射勝利フラグがあるかチェック
    is_counter = st.session_state.get("counter_finish", False)
    
    bg_color = "rgba(255, 215, 0, 0.3)" if is_counter else "rgba(255, 0, 0, 0.2)"
    border_color = "#FFD700" if is_counter else "#FF0000"
    main_text = "FULL COUNTER WIN!" if is_counter else "GAME OVER"
    text_color = "#FFD700" if is_counter else "#FF0000"

    st.markdown(f"""
        <div style="text-align: center; padding: 50px; background-color: {bg_color}; 
                    border-radius: 20px; border: 8px double {border_color}; margin: 20px 0;
                    box-shadow: 0 0 20px {border_color}; animation: pulse 2s infinite;">
            <h1 style="color: {text_color}; font-size: 80px; margin-bottom: 10px; text-shadow: 2px 2px 10px black;">{main_text}</h1>
            <h2 style="color: white; font-size: 40px;">🏆 Winner: {winner}</h2>
            <p style="color: #EEE;">{'相手の力を利用して勝利を掴み取った！' if is_counter else '激闘の末、勝者が決定した！'}</p>
        </div>
        <style>
            @keyframes pulse {{
                0% {{ transform: scale(1); opacity: 1; }}
                50% {{ transform: scale(1.02); opacity: 0.8; }}
                100% {{ transform: scale(1); opacity: 1; }}
            }}
        </style>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 もう一度遊ぶ (リセット)"):
        # フラグもリセット
        st.session_state.counter_finish = False
        cards = list(CARD_DB.keys()); d = cards * 2; random.shuffle(d)
        update_db({"hp1": 100, "hp2": 100, "p1_hand":[], "p2_hand":[], "p1_used_innate":[], "p2_used_innate":[], "turn":"P1", "turn_count":0, "pending_damage":0, "phase":"ATK", "deck": d})
        st.rerun()
    st.stop()
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
# --- 防御側の処理 ---
if not is_my_turn and current_phase == "DEF":
    st.warning(f"⚠️ 相手の攻撃！ **{pending_dmg}** ダメージ！")
    my_hand = data.get(f"{me}_hand", [])
    guards = [CARD_DB[n] for n in my_hand if n in CARD_DB and CARD_DB[n].type == "guard"]
    
    cols = st.columns(len(guards) + 1)
    for i, g in enumerate(guards):
        if cols[i].button(f"🛡️ {g.name}"):
            upd = {
                "pending_damage": 0,
                "phase": "ATK",
                "turn": f"P{my_id}",
                "turn_count": data["turn_count"] + 1,
                f"{me}_hand": [n for n in my_hand if n != g.name]
            }
            
            # --- 反射・軽減ロジック ---
            if "反射" in g.cond_text or "返し" in g.cond_text:
                reflect_dmg = int(pending_dmg * g.power)
                new_opp_hp = data[f"hp{opp_id}"] - reflect_dmg
                upd[f"hp{opp_id}"] = new_opp_hp
                
                # 相手のHPが0以下になったら、セッションに反射勝利フラグを立てる
                if new_opp_hp <= 0:
                    st.session_state.counter_finish = True
                
                st.success(f"✨ 反射！ 相手に {reflect_dmg} ダメージ返した！")
                
                # 「トゲトゲの盾」のような軽減併用タイプの場合
                if "軽減" in g.cond_text:
                    upd[f"hp{my_id}"] = data[f"hp{my_id}"] - max(0, pending_dmg - (pending_dmg * 0.5))
            else:
                # 通常のガード（軽減）
                upd[f"hp{my_id}"] = data[f"hp{my_id}"] - max(0, pending_dmg - g.power)
            
            update_db(upd)
            time.sleep(1) # 演出を見せるため
            st.rerun()
            
    if cols[-1].button("そのまま受ける"):
        update_db({f"hp{my_id}": data[f"hp{my_id}"] - pending_dmg, "pending_damage": 0, "phase": "ATK", "turn": f"P{my_id}", "turn_count": data["turn_count"]+1})
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
            play_se(DICE_ROLL_SE)
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
    play_se(SE_URL)
    st.rerun()

with st.sidebar:
    if st.button("🚨 全リセット"):
        all_cards = list(CARD_DB.keys()); new_deck = all_cards * 2; random.shuffle(new_deck)
        update_db({"hp1": 100, "hp2": 100, "p1_hand": [], "p2_hand": [], "p1_used_innate": [], "p2_used_innate": [], "turn": "P1", "turn_count": 0, "pending_damage": 0, "phase": "ATK", "deck": new_deck})
        st.rerun()














