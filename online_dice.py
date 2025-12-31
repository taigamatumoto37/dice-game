import streamlit as st
from supabase import create_client
import random
import streamlit.components.v1 as components

# =============================
# 効果音
# =============================
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

SE_URL = "https://github.com/taigamatumoto37/dice-game/raw/main/決定ボタンを押す8.mp3"
DICE_ROLL_SE = SE_URL
BGM_URL = "https://github.com/taigamatumoto37/dice-game/raw/main/001_睡眠用BGM.mp3"

components.html(
    f"""
    <audio id="bgm" src="{BGM_URL}" loop></audio>
    <script>
        window.parent.document.body.addEventListener('click', function() {{
            const audio = document.getElementById('bgm');
            if (audio.paused) audio.play().catch(()=>{{}});
        }}, {{ once: true }});
    </script>
    """,
    height=0,
)

# =============================
# Supabase
# =============================
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

def get_data():
    return supabase.table("game_state").select("*").eq("id", 1).execute().data[0]

def update_db(data):
    supabase.table("game_state").update(data).eq("id", 1).execute()

# =============================
# カードクラス
# =============================
class Card:
    def __init__(self, name, ctype, power, cond, text,
                 guard_mode=None, reflect_ratio=0.0):
        self.name = name
        self.type = ctype
        self.power = power
        self.cond = cond
        self.text = text
        self.guard_mode = guard_mode
        self.reflect_ratio = reflect_ratio

# =============================
# ダイス条件
# =============================
def check_pair(d): return any(d.count(x) >= 2 for x in set(d))
def check_three(d): return any(d.count(x) >= 3 for x in set(d))
def check_yahtzee(d): return len(set(d)) == 1
def check_straight(d):
    s = sorted(set(d))
    return s == list(range(min(s), min(s) + 5))

# =============================
# カードDB
# =============================
CARD_DB = {
    # --- 攻撃 ---
    "ジェミニ・ダガー": Card("ジェミニ・ダガー","attack",12,check_pair,"ペア"),
    "トライ・ブラスト": Card("トライ・ブラスト","attack",20,check_three,"スリーカード"),
    "クアッド・ボルテックス": Card(
        "クアッド・ボルテックス","attack",35,
        lambda d: any(d.count(x) >= 4 for x in set(d)),
        "フォーカード"
    ),
    "五行封印斬": Card("五行封印斬","attack",60,check_yahtzee,"ヤッツィー"),
    "スモール・エッジ": Card(
        "スモール・エッジ","attack",25,
        lambda d: len(set(d)) >= 3,
        "3種類以上の出目"
    ),
    "スカイ・ストライク": Card(
        "スカイ・ストライク","attack",35,
        lambda d: len(set(d)) >= 4,
        "4種類以上の出目"
    ),
    "フルハウス・バスター": Card(
        "フルハウス・バスター","attack",40,
        lambda d: len(set(d)) <= 3,
        "出目が3種類以下"
    ),
    "偶数の審判": Card(
        "偶数の審判","attack",30,
        lambda d: any(x % 2 == 0 for x in d),
        "偶数が1つでもある"
    ),
    "奇数の洗礼": Card(
        "奇数の洗礼","attack",30,
        lambda d: any(x % 2 != 0 for x in d),
        "奇数が1つでもある"
    ),
    "ハイ・ローラー": Card(
        "ハイ・ローラー","attack",35,
        lambda d: sum(d) >= 18,
        "合計18以上"
    ),
    "ロー・ローラー": Card(
        "ロー・ローラー","attack",35,
        lambda d: sum(d) <= 15,
        "合計15以下"
    ),

    # --- 回復 ---
    "慈悲 of 祝福": Card("慈悲 of 祝福","heal",20,check_pair,"ペア"),
    "聖なる祈り": Card(
        "聖なる祈り","heal",30,
        lambda d: any(x in d for x in (1, 6)),
        "1か6がある"
    ),
    "生命の輝き": Card("生命の輝き","heal",45,check_three,"スリーカード"),
    "再生の福音": Card("再生の福音","heal",80,check_yahtzee,"ヤッツィー"),
    "プチ・ヒール": Card("プチ・ヒール","heal",10,lambda d: True,"無条件"),
    "女神の休息": Card("女神の休息","heal",15,lambda d: True,"無条件"),
    "癒しの波動": Card("癒しの波動","heal",25,check_pair,"ペア"),
    "エナジー・ドレイン": Card(
        "エナジー・ドレイン","heal",45,
        lambda d: sum(d) >= 20,
        "合計20以上"
    ),

    # --- 防御 ---
    "アイアン・ウォール": Card(
        "アイアン・ウォール","guard",15,
        lambda d: True,"15軽減",
        guard_mode="reduce"
    ),
    "マジック・ミラー": Card(
        "マジック・ミラー","guard",30,
        lambda d: True,"30軽減",
        guard_mode="reduce"
    ),
    "ナイト・シールド": Card(
        "ナイト・シールド","guard",25,
        lambda d: True,"25軽減",
        guard_mode="reduce"
    ),
    "ホーリー・バリア": Card(
        "ホーリー・バリア","guard",45,
        lambda d: True,"45軽減",
        guard_mode="reduce"
    ),
    "ミラー・シールド": Card(
        "ミラー・シールド","guard",0,
        lambda d: True,"100%反射",
        guard_mode="reflect", reflect_ratio=1.0
    ),
    "トゲトゲの盾": Card(
        "トゲトゲの盾","guard",0,
        lambda d: True,"50%反射+50%軽減",
        guard_mode="hybrid", reflect_ratio=0.5
    ),
}


# =============================
# 固有デッキ
# =============================

INNATE_DECK = [
    Card("固有:トリニティ","attack",20,check_three,"スリーカード"),
    Card("固有:五連光破斬","attack",30,check_straight,"ストレート"),
    Card("固有:神罰 of 五連星","attack",50,check_yahtzee,"ヤッツィー"),
    Card("固有:双撃の構え","attack",15,check_pair,"ペア"),
    Card(
        "固有:生命の共鳴","heal",25,
        lambda d: len({x for x in d if d.count(x) >= 2}) >= 2,
        "2ペア"
    ),
    Card(
        "固有:等位の福音","heal",40,
        lambda d: len(set(d)) == 2 and any(d.count(x) == 3 for x in set(d)),
        "フルハウス"
    ),
    Card("固有:轟力・大山波","attack",35,lambda d: sum(d) >= 22,"合計22以上"),
    Card("固有:静寂・小波斬","attack",25,lambda d: sum(d) <= 12,"合計12以下"),
]
for c in INNATE_DECK:
    CARD_DB[c.name] = c

def initial_hand():
    return list(CARD_DB.keys())

# =============================
# メイン
# =============================
data = get_data()

if not data.get("p1_hand") and not data.get("p2_hand"):
    update_db({
        "p1_hand": initial_hand(),
        "p2_hand": initial_hand()
    })
    st.rerun()

role = st.sidebar.radio("役割",["Player 1","Player 2"])
me, opp, my_id, opp_id = ("p1","p2",1,2) if role=="Player 1" else ("p2","p1",2,1)

st.title("⚔️ YAHTZEE TACTICS ⚔️")

# =============================
# HP表示（上限なし）
# =============================
for i in (1,2):
    st.write(f"### PLAYER {i} ❤️ {max(0,data[f'hp{i}'])}")

# =============================
# 勝敗判定
# =============================
if data["hp1"] <= 0 or data["hp2"] <= 0:
    winner = "Player 2" if data["hp1"] <= 0 else "Player 1"
    title = "FULL COUNTER WIN!" if data.get("counter_finish") else "GAME OVER"
    st.markdown(f"## {title}\n### 🏆 {winner}")
    if st.button("リセット"):
        update_db({
            "hp1":100,"hp2":100,
            "pending_damage":0,
            "phase":"ATK",
            "turn":"P1",
            "turn_count":0,
            "counter_finish":False,
            "p1_hand":initial_hand(),
            "p2_hand":initial_hand(),
        })
        st.rerun()
    st.stop()

# =============================
# フェーズ
# =============================
is_my_turn = data["turn"] == f"P{my_id}"
phase = data["phase"]
pending = data["pending_damage"]

# =============================
# 防御フェーズ
# =============================
if not is_my_turn and phase == "DEF":
    st.warning(f"⚠️ {pending} ダメージ")
    my_hand = data[f"{me}_hand"]
    opp_dice = data.get(f"{opp}_dice",[1]*5)

    for name in my_hand:
        c = CARD_DB[name]
        if c.type=="guard" and c.cond(opp_dice):
            if st.button(f"🛡️ {c.name}"):
                upd = {
                    "pending_damage":0,
                    "phase":"ATK",
                    "turn":f"P{my_id}",
                    "turn_count":data["turn_count"]+1,
                    f"{me}_hand":[n for n in my_hand if n!=name]
                }

                if c.guard_mode=="reflect":
                    dmg=int(pending*c.reflect_ratio)
                    upd[f"hp{opp_id}"]=max(0,data[f"hp{opp_id}"]-dmg)

                elif c.guard_mode=="hybrid":
                    reflect=int(pending*c.reflect_ratio)
                    remain=pending-reflect
                    upd[f"hp{opp_id}"]=max(0,data[f"hp{opp_id}"]-reflect)
                    upd[f"hp{my_id}"]=max(0,data[f"hp{my_id}"]-remain)

                else:
                    dmg=max(0,pending-c.power)
                    upd[f"hp{my_id}"]=max(0,data[f"hp{my_id}"]-dmg)

                if upd.get(f"hp{opp_id}",1)<=0:
                    upd["counter_finish"]=True

                update_db(upd)
                st.rerun()

    if st.button("そのまま受ける"):
        update_db({
            f"hp{my_id}":max(0,data[f"hp{my_id}"]-pending),
            "pending_damage":0,
            "phase":"ATK",
            "turn":f"P{my_id}",
            "turn_count":data["turn_count"]+1
        })
        st.rerun()
    st.stop()

# =============================
# 攻撃フェーズ
# =============================
if is_my_turn:
    if st.session_state.get("last_turn")!=data["turn_count"]:
        st.session_state.dice=[random.randint(1,6) for _ in range(5)]
        st.session_state.rolls=2
        st.session_state.keep=[False]*5
        st.session_state.last_turn=data["turn_count"]
        update_db({f"{me}_dice":st.session_state.dice})

    st.write("🎲 ダイス")
    for i in range(5):
        st.session_state.keep[i]=st.checkbox(
            f"Keep{i}",value=st.session_state.keep[i],
            key=f"k{i}{my_id}{data['turn_count']}"
        )
        st.write(st.session_state.dice[i])

    if st.session_state.rolls>0 and st.button("振る"):
        play_se(DICE_ROLL_SE)
        st.session_state.dice=[
            v if st.session_state.keep[i] else random.randint(1,6)
            for i,v in enumerate(st.session_state.dice)
        ]
        st.session_state.rolls-=1
        update_db({f"{me}_dice":st.session_state.dice})
        st.rerun()

    st.write("⚔️ スキル")
    my_hand=data[f"{me}_hand"]
    for name in my_hand:
        c=CARD_DB[name]
        if c.type!="guard" and c.cond(st.session_state.dice):
            if st.button(c.name):
                play_se(SE_URL)
                if c.type=="attack":
                    update_db({
                        "pending_damage":data["pending_damage"]+c.power,
                        "phase":"DEF"
                    })
                else:
                    update_db({
                        f"hp{my_id}":data[f"hp{my_id}"]+c.power,
                        "turn":f"P{opp_id}",
                        "turn_count":data["turn_count"]+1
                    })
                st.rerun()
