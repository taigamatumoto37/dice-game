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
            audio.volume = 0.6; // 音量はここで調節(0.0〜1.0)
            audio.play();
        </script>
        """,
        height=0,
    )

# あなたのGitHubから取得した「Raw」URL
SE_URL = "https://github.com/taigamatumoto37/dice-game/raw/5c9c1c88d3d308d48494ed197ece6eb88a5ea8d3/%E6%B1%BA%E5%AE%9A%E3%83%9C%E3%82%BF%E3%83%B3%E3%82%92%E6%8A%BC%E3%81%998.mp3"
# GitHubのRaw URL (あなたがアップロードしたファイル)
bgm_url = "https://github.com/taigamatumoto37/dice-game/raw/main/001_%E3%80%90%E7%9D%A1%E7%9C%A030%E5%88%86%E5%89%8D%E7%94%A8%E3%80%91%E7%86%9F%E7%9D%A1%E3%81%A7%E3%81%8D%E3%82%8B%E7%9D%A1%E7%9C%A0%E7%94%A8BGM%20Smooth%20Jazz%E3%80%90%E5%BA%83%E5%91%8A%E3%81%AA%E3%81%97%E3%80%91Deep%20Sleep%2C%20Relaxing%2C%20Healing%2C%20Sleep%20Music%2C%2030%20miniutes.mp3"

# BGM再生用のHTML/JavaScript
components.html(
    f"""
    <audio id="bgm" src="{bgm_url}" loop></audio>
    <script>
        // ブラウザの自動再生制限を回避するため、画面のどこかをクリックした瞬間に再生を開始する
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

# サイドバーに音量調節などの案内を表示
st.sidebar.markdown("---")
st.sidebar.markdown("🎵 **BGM: Smooth Jazz**")
st.sidebar.caption("※画面のどこかをクリックすると再生が始まります")
# BGMの設定（YouTubeなどの直リンクや、GitHubに上げたMP3のURLなどを指定）
# ※ここでは著作権フリーのサンプル音源を入れています
bgm_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"

components.html(
    f"""
    <audio id="bgm" src="{bgm_url}" loop></audio>
    <script>
        // ユーザーが画面のどこかをクリックした瞬間に再生を開始する
        // (ブラウザの自動再生禁止制限を回避するため)
        document.body.addEventListener('click', function() {{
            var audio = document.getElementById('bgm');
            if (audio.paused) {{
                audio.play();
            }}
        }}, {{ once: true }});
    </audio>
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

# --- 拡張版カードデータベース (30枚) ---
CARD_DB = {
    # 【攻撃系：基本 - 頻繁に撃てる】
    "ジェミニ・ダガー": Card("ジェミニ・ダガー", "attack", 12, check_pair, "ペア"),
    "トライ・ブラスト": Card("トライ・ブラスト", "attack", 20, check_three, "スリーカード"),
    "クアッド・ボルテックス": Card("クアッド・ボルテックス", "attack", 35, lambda d: any(d.count(x) >= 4 for x in set(d)), "フォーカード"),
    "五行封印斬": Card("五行封印斬", "attack", 60, check_yahtzee, "ヤッツィー (ロマン砲)"),
    
    # 【攻撃系：ストレート - 判定を緩和】
    "スモール・エッジ": Card("スモール・エッジ", "attack", 25, lambda d: len(set(d)) >= 3, "3種類以上の出目"), # 4連から3種へ
    "スカイ・ストライク": Card("スカイ・ストライク", "attack", 35, lambda d: len(set(d)) >= 4, "4種類以上の出目"), # Lストから4種へ
    
    # 【回復・防御系 - 立て直しやすく】
    "慈悲 of 祝福": Card("慈悲 of 祝福", "heal", 20, check_pair, "ペア"),
    "聖なる祈り": Card("聖なる祈り", "heal", 30, lambda d: any(x in d for x in [1, 6]), "1か6がある"), # ペアから1枚あればOKへ
    "生命の輝き": Card("生命の輝き", "heal", 45, check_three, "スリーカード"),
    "再生の福音": Card("再生の福音", "heal", 80, check_yahtzee, "ヤッツィー"),

    # 【特殊・高難易度系】
    "フルハウス・バスター": Card("フルハウス・バスター", "attack", 40, lambda d: len(set(d)) <= 3, "出目が3種類以下"), # 条件緩和
    "偶数の審判": Card("偶数の審判", "attack", 30, lambda d: any(x % 2 == 0 for x in d), "偶数が1つでもある"),
    "奇数の洗礼": Card("奇数の洗礼", "attack", 30, lambda d: any(x % 2 != 0 for x in d), "奇数が1つでもある"),
    "ハイ・ローラー": Card("ハイ・ローラー", "attack", 35, lambda d: sum(d) >= 18, "合計18以上"), # 25から18へ
    "ロー・ローラー": Card("ロー・ローラー", "attack", 35, lambda d: sum(d) <= 15, "合計15以下"), # 10から15へ
    
    # 【バリエーション追加】
    "連撃の小太刀": Card("連撃の小太刀", "attack", 15, check_pair, "ペア"),
    "三連重破弾": Card("三連重破弾", "attack", 28, check_three, "スリーカード"),
    "天の逆鱗": Card("天の逆鱗", "attack", 70, check_yahtzee, "ヤッツィー"),
    "プチ・ヒール": Card("プチ・ヒール", "heal", 10, lambda d: True, "無条件(発動のみ)"),
    "大地の怒り": Card("大地の怒り", "attack", 30, lambda d: sum(d) >= 15, "合計15以上"),
    "木漏れ日の唄": Card("木漏れ日の唄", "heal", 15, lambda d: len(set(d)) >= 2, "2種類以上の出目"),
    "ブラッド・契約": Card("ブラッド・契約", "attack", 50, lambda d: d.count(4) >= 2, "4のペア"), # 3枚から2枚へ
    "サンダー・ボルト": Card("サンダー・ボルト", "attack", 25, lambda d: 5 in d or 6 in d, "5か6がある"), # andからorへ
    "フリーズ・レクイエム": Card("フリーズ・レクイエム", "attack", 25, lambda d: 1 in d or 2 in d, "1か2がある"), # andからorへ
    "毒の霧": Card("毒の霧", "attack", 18, lambda d: len(set(d)) >= 4, "4種類以上の出目"), 
    "光の防壁": Card("光の防壁", "heal", 35, lambda d: check_pair(d), "ペア (条件緩和)"),
    "ダブル・インパクト": Card("ダブル・インパクト", "attack", 25, check_pair, "ペア"),
    "ジャッジメント": Card("ジャッジメント", "attack", 99, lambda d: sum(d) >= 28, "合計28以上(ほぼ6)"), # 30固定から緩和
    "ゼロ・グラビティ": Card("ゼロ・グラビティ", "attack", 99, lambda d: sum(d) <= 7, "合計7以下(ほぼ1)"), # 5固定から緩和
    "星屑の願い": Card("星屑の願い", "heal", 35, lambda d: len(set(d)) >= 4, "4種類以上の出目")
}
INNATE_DECK = [
    Card("固有:トリニティ", "attack", 20, check_three, "スリーカード"),
    Card("固有:五連光破斬", "attack", 30, check_straight, "ストレート"),
    Card("固有:神罰 of 五連星", "attack", 50, check_yahtzee, "ヤッツィー")
]

def get_data(): return supabase.table("game_state").select("*").eq("id", 1).execute().data[0]
def update_db(u): 
    try: supabase.table("game_state").update(u).eq("id", 1).execute()
    except: pass

# --- 3. CSS (写真のUI再現) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    .hp-bar-container { background: #333; height: 10px; border-radius: 5px; margin-top: 5px; }
    .hp-bar-fill { background: #00FFAA; height: 100%; border-radius: 5px; transition: width 0.5s; }
    .dice-slot {
        background: rgba(0, 0, 0, 0.5); border: 2px solid #00FFFF; border-radius: 10px;
        height: 80px; display: flex; align-items: center; justify-content: center;
        font-size: 35px; color: #00FFFF; box-shadow: 0 0 15px rgba(0, 255, 255, 0.3);
    }
    .opp-dice { border-color: #FF4B4B; color: #FF4B4B; height: 50px; font-size: 20px; box-shadow: none; opacity: 0.7; }
    div.stButton > button {
        background-color: #FF5555 !important; color: white !important;
        width: 100% !important; border-radius: 5px !important; font-weight: bold !important;
    }
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
        st.write(f"PLAYER {p_num} {'🔥' if data['turn'] == f'P{p_num}' else ''}")
        st.write(f"HP {hp} / 150")
        st.markdown(f"<div class='hp-bar-container'><div class='hp-bar-fill' style='width:{(hp/150)*100}%'></div></div>", unsafe_allow_html=True)

# --- 共通：相手のダイス表示 ---
st.write(f"### 🛡️ 相手(P{opp_id})の刻印")
o_dice = data.get(f"{opp}_dice", [1,1,1,1,1])
oc = st.columns(5)
for i in range(5):
    oc[i].markdown(f"<div class='dice-slot opp-dice'>{o_dice[i]}</div>", unsafe_allow_html=True)

st.divider()

# --- ターン管理 (ここから入れ替え) ---
is_my_turn = (data["turn"] == f"P{my_id}")

# 1. ターンの初期化処理
if is_my_turn:
    if st.session_state.get("last_processed_turn") != data["turn_count"]:
        st.session_state.dice = [random.randint(1, 6) for _ in range(5)]
        st.session_state.rolls = 2
        st.session_state.keep = [False] * 5
        st.session_state.last_processed_turn = data["turn_count"]
        update_db({f"{me}_dice": st.session_state.dice})
        st.rerun()



# --- 効果音の設定 ---
# あなたがアップロードした決定音のRaw URL
DICE_FIX_SE = "https://github.com/taigamatumoto37/dice-game/raw/5c9c1c88d3d308d48494ed197ece6eb88a5ea8d3/%E6%B1%BA%E5%AE%9A%E3%83%9C%E3%82%BF%E3%83%B3%E3%82%92%E6%8A%BC%E3%81%998.mp3"
# 振り始めの音（もしあれば。なければ決定音と同じでもOK）
DICE_ROLL_SE = "https://otologic.jp/free/se/wav/dice-roll1.wav" 

def play_se(url):
    """効果音を即時再生する関数"""
    components.html(
        f"""
        <script>
            var audio = new Audio("{url}");
            audio.volume = 0.7;
            audio.play();
        </script>
        """,
        height=0,
    )


if is_my_turn:
    # 現在の残り振れる回数を表示
    remaining_rolls = st.session_state.get("rolls", 0)
    st.write(f"### 🎲 あなたの刻印 (残りリロール回数: {remaining_rolls})")
    cols = st.columns(5)
    for i in range(5):
        # キープ（ホールド）機能のチェックボックス
        is_keep = st.checkbox(f"Keep", key=f"keep_{i}_{data['turn_count']}", value=st.session_state.get("keep", [False]*5)[i])
        st.session_state.keep[i] = is_keep
        cols[i].markdown(f"<div class='dice-slot'>{'?' if not any(st.session_state.dice) else st.session_state.dice[i]}</div>", unsafe_allow_html=True)

    # 振り直しボタン（回数制限あり）
    if remaining_rolls > 0:
        if st.button(f"🎲 ダイスを振る (残り{remaining_rolls}回)", use_container_width=True):
            # 1. 決定音を鳴らす（あなたのGitHub音源）
            play_se(DICE_FIX_SE)
            
            # 2. アニメーション演出
            dice_placeholders = [st.empty() for _ in range(5)]
            for _ in range(10):
                temp_vals = [random.randint(1, 6) for _ in range(5)]
                for i in range(5):
                    if not st.session_state.keep[i]:
                        dice_placeholders[i].markdown(f"<div class='dice-slot' style='color:#555;'>{temp_vals[i]}</div>", unsafe_allow_html=True)
                time.sleep(0.05)
            
            # 3. 出目確定（キープされていないものだけ更新）
            for i in range(5):
                if not st.session_state.keep[i]:
                    st.session_state.dice[i] = random.randint(1, 6)
            
            # 4. 状態更新
            st.session_state.rolls -= 1
            update_db({f"{me}_dice": st.session_state.dice})
            st.rerun()
    else:
        st.warning("⚠️ これ以上ダイスは振れません。スキルを発動するか、ターンを終了してください。")

else:
    # 相手のターン時は現在のダイスを表示のみ（または0に）
    st.info("相手のターンです。作戦を練りましょう...")
    st.session_state.dice = [0,0,0,0,0]
# --- 2. 自分のカード一覧（DBから自分専用の手札を取得） ---
st.write(f"### ⚔️ PLAYER {my_id} のスキル")

# DBから最新の自分専用データを取得
my_hand_from_db = list(data.get(f"{me}_hand", []))
my_used_innate = list(data.get(f"{me}_used_innate", []))

# 表示用リスト（pool）の作成：固有スキル - 使用済み ＋ 手札
pool = [c for c in INNATE_DECK if c.name not in my_used_innate]
for h_name in my_hand_from_db:
    if h_name in CARD_DB:
        pool.append(CARD_DB[h_name])

sc = st.columns(3)

for idx, card in enumerate(pool):
    # 自分のターンかつダイスがある時だけ役判定
    is_ready = card.condition_func(st.session_state.dice) if (is_my_turn and any(st.session_state.dice)) else False
    
    with sc[idx % 3]:
        st.markdown(f"""
        <div class='skill-card' style='border-color: {"#00FFAA" if is_ready else "#FF5555"};'>
            <b style='color: {"#00FFAA" if is_ready else "white"};'>{card.name}</b><br>
            <small>威力：{card.power} | 条件：{card.cond_text}</small>
        </div>
        """, unsafe_allow_html=True)
        
        if is_my_turn and is_ready:
            if st.button("発動", key=f"atk_{card.name}_{idx}_{data['turn_count']}"):
                # 決定音を再生
                play_se(SE_URL)
                
                # 更新データの作成
                upd = {
                    "turn": f"P{opp_id}", 
                    "turn_count": data["turn_count"] + 1
                }
                
                # ダメージ・回復計算
                if card.type == "attack":
                    upd[f"hp{opp_id}"] = data[f"hp{opp_id}"] - card.power
                else:
                    upd[f"hp{my_id}"] = data[f"hp{my_id}"] + card.power
                
                # 消費処理：固有か手札かで分ける
                if "固有" in card.name:
                    upd[f"{me}_used_innate"] = my_used_innate + [card.name]
                else:
                    # 手札からこのカードを1枚だけ削除
                    new_hand = list(my_hand_from_db)
                    if card.name in new_hand:
                        new_hand.remove(card.name)
                    upd[f"{me}_hand"] = new_hand
                
                update_db(upd)
                st.rerun()

# 3. 終了処理と自動リロード

if is_my_turn:
    if st.button("ターンを終了してドロー", key=f"end_{data['turn_count']}"):
        latest = get_data()
        deck = latest.get("deck", [])
        
        if deck:
            # 山札の先頭から1枚引く
            new_card = deck.pop(0) 
            if len(hand) < 5:
                hand.append(new_card)
                st.session_state.hand = hand
        
        update_db({
            "deck": deck, 
            "turn": f"P{opp_id}", 
            "turn_count": latest["turn_count"] + 1
        })
        st.rerun()
# --- ここまで入れ替え ---


# リセット (サイドバー)
if st.sidebar.button("🚨 全リセット"):
    # 全カードリストを取得してシャッフル
    all_cards = list(CARD_DB.keys())
    new_deck = all_cards * 2  # 各カード2枚ずつ、合計60枚の山札
    random.shuffle(new_deck)
    
    update_db({
        "hp1": 150, "hp2": 150, 
        "turn": "P1", "turn_count": 0, 
        "p1_used_innate": [], "p2_used_innate": [], 
        "p1_dice": [1,1,1,1,1], "p2_dice": [1,1,1,1,1], 
        "deck": new_deck  # ここで全種類の入った山札をセット
    })
    st.session_state.hand = []
    st.rerun()










