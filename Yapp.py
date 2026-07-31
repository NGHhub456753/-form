import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.service_account import Credentials
import gspread
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ==========================================
# ⚙️ 基本設定 & 定数
# ==========================================
st.set_page_config(
    page_title="折り紙体験ワークショップ 参加予約", page_icon="📝"
)

SPREADSHEET_NAME = "イベント予約一覧"
CONTACT_EMAIL = "aonisai0111@gmail.com"
ADMIN_EMAIL = "aonisai0111@gmail.com"
CANCEL_APP_URL = "https://djks33sfzskwjzeam4mbcr.streamlit.app/"


# ==========================================
# 🎨 アニメーション・デザイン専用ブロック
# ==========================================
def trigger_origami_crane_animation():
  """画面左下から中央を通り、大量のシラサギが右上へ飛び立つアニメーション"""
  js_code = """
    <script>
    (function() {
        let doc = window.parent.document;
        
        let oldElem = doc.getElementById('crane-anim-layer');
        if (oldElem) { oldElem.remove(); }

        let style = doc.createElement('style');
        style.textContent = `
            /* 画面の【左下】からスタートして【右上】へ画面を大きく切る軌道 */
            @keyframes flyDiagonal {
                0% {
                    transform: translate(0vw, 85vh) scale(0.5) rotate(-35deg);
                    opacity: 0;
                }
                15% {
                    opacity: 1;
                }
                75% {
                    opacity: 0.9;
                }
                100% {
                    transform: translate(110vw, -25vh) scale(1.1) rotate(-20deg);
                    opacity: 0;
                }
            }
            @keyframes wingFlap {
                0%, 100% { transform: rotate(0deg) scaleY(1); }
                50% { transform: rotate(-25deg) scaleY(0.65); }
            }
            .crane-anim-container {
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                width: 100vw !important;
                height: 100vh !important;
                pointer-events: none !important;
                z-index: 9999999 !important;
                overflow: hidden !important;
            }
            .egret-bird {
                position: absolute;
                top: 0;
                left: 0;
                width: 80px;
                height: 80px;
                animation: flyDiagonal 2.3s cubic-bezier(0.2, 0.8, 0.4, 1) forwards;
            }
            .egret-wing-part {
                transform-origin: 45% 55%;
                animation: wingFlap 0.18s infinite ease-in-out;
            }
        `;
        doc.head.appendChild(style);

        let container = doc.createElement('div');
        container.id = 'crane-anim-layer';
        container.className = 'crane-anim-container';
        
        container.innerHTML = `
            <svg style="display:none;">
                <g id="crane-svg-shape">
                    <polygon points="5,35 28,32 35,42 20,45" fill="#CBD5E1"/>
                    <polygon points="28,32 38,20 42,26 35,42" fill="#FFFFFF"/>
                    <polygon points="38,20 48,32 42,42 35,42" fill="#F8FAFC"/>
                    <polygon points="45,55 55,48 78,72 58,82" fill="#FFFFFF"/>
                    <polygon points="5,35 28,32 20,30" fill="#FFA500"/>
                    <circle cx="30" cy="27" r="1.8" fill="#1E293B"/>
                    <g class="egret-wing-part">
                        <polygon points="42,42 88,10 65,52" fill="#FFFFFF"/>
                        <polygon points="65,52 88,10 78,72" fill="#E2E8F0"/>
                    </g>
                </g>
            </svg>
            <!-- 15羽のシラサギ群（配置・サイズ・出現時間をばらバラに調整） -->
            <div class="egret-bird" style="margin-left: -5vw; margin-top: 5vh; animation-delay: 0s; transform: scale(1.0);"><svg viewBox="0 0 100 100"><use href="#crane-svg-shape"/></svg></div>
            <div class="egret-bird" style="margin-left: -10vw; margin-top: 12vh; animation-delay: 0.1s; transform: scale(0.85);"><svg viewBox="0 0 100 100"><use href="#crane-svg-shape"/></svg></div>
            <div class="egret-bird" style="margin-left: -2vw; margin-top: 18vh; animation-delay: 0.2s; transform: scale(1.1);"><svg viewBox="0 0 100 100"><use href="#crane-svg-shape"/></svg></div>
            <div class="egret-bird" style="margin-left: -8vw; margin-top: 25vh; animation-delay: 0.3s; transform: scale(0.9);"><svg viewBox="0 0 100 100"><use href="#crane-svg-shape"/></svg></div>
            <div class="egret-bird" style="margin-left: -15vw; margin-top: 20vh; animation-delay: 0.4s; transform: scale(0.75);"><svg viewBox="0 0 100 100"><use href="#crane-svg-shape"/></svg></div>
            
            <div class="egret-bird" style="margin-left: -4vw; margin-top: 10vh; animation-delay: 0.5s; transform: scale(0.95);"><svg viewBox="0 0 100 100"><use href="#crane-svg-shape"/></svg></div>
            <div class="egret-bird" style="margin-left: -12vw; margin-top: 4vh; animation-delay: 0.6s; transform: scale(0.8);"><svg viewBox="0 0 100 100"><use href="#crane-svg-shape"/></svg></div>
            <div class="egret-bird" style="margin-left: -6vw; margin-top: 22vh; animation-delay: 0.7s; transform: scale(1.05);"><svg viewBox="0 0 100 100"><use href="#crane-svg-shape"/></svg></div>
            <div class="egret-bird" style="margin-left: -18vw; margin-top: 15vh; animation-delay: 0.8s; transform: scale(0.7);"><svg viewBox="0 0 100 100"><use href="#crane-svg-shape"/></svg></div>
            <div class="egret-bird" style="margin-left: -3vw; margin-top: 28vh; animation-delay: 0.9s; transform: scale(1.0);"><svg viewBox="0 0 100 100"><use href="#crane-svg-shape"/></svg></div>
            
            <div class="egret-bird" style="margin-left: -9vw; margin-top: 8vh; animation-delay: 1.0s; transform: scale(0.85);"><svg viewBox="0 0 100 100"><use href="#crane-svg-shape"/></svg></div>
            <div class="egret-bird" style="margin-left: -14vw; margin-top: 24vh; animation-delay: 1.1s; transform: scale(0.9);"><svg viewBox="0 0 100 100"><use href="#crane-svg-shape"/></svg></div>
            <div class="egret-bird" style="margin-left: -7vw; margin-top: 16vh; animation-delay: 1.2s; transform: scale(1.15);"><svg viewBox="0 0 100 100"><use href="#crane-svg-shape"/></svg></div>
            <div class="egret-bird" style="margin-left: -11vw; margin-top: 2vh; animation-delay: 1.3s; transform: scale(0.75);"><svg viewBox="0 0 100 100"><use href="#crane-svg-shape"/></svg></div>
            <div class="egret-bird" style="margin-left: -5vw; margin-top: 30vh; animation-delay: 1.4s; transform: scale(0.95);"><svg viewBox="0 0 100 100"><use href="#crane-svg-shape"/></svg></div>
        `;
        
        doc.body.appendChild(container);

        // 全員飛び去るまで（約4.0秒後）保持して自動消去
        setTimeout(() => {
            if (container) container.remove();
        }, 4000);
    })();
    </script>
    """
  components.html(js_code, height=0, width=0)


# ==========================================
# 🛠️ 外部連携関数（スプレッドシート & メール）
# ==========================================
@st.cache_resource
def get_gspread_client():
  scopes = [
      "https://www.googleapis.com/auth/spreadsheets",
      "https://www.googleapis.com/auth/drive",
  ]
  service_account_info = dict(st.secrets["gcp_service_account"])
  service_account_info["private_key"] = service_account_info[
      "private_key"
  ].replace("\\n", "\n")

  credentials = Credentials.from_service_account_info(
      service_account_info, scopes=scopes
  )
  return gspread.authorize(credentials)


def get_worksheet():
  client = get_gspread_client()
  sheet = client.open(SPREADSHEET_NAME)
  return sheet.sheet1


def send_email(to_email, subject, body):
  try:
    sender_email = st.secrets["smtp"]["email"]
    sender_password = st.secrets["smtp"]["password"]

    msg = MIMEMultipart()
    msg["From"] = f"イベント事務局 <{sender_email}>"
    msg["To"] = to_email
    msg["Reply-To"] = CONTACT_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    recipients = list({to_email, ADMIN_EMAIL, CONTACT_EMAIL})

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, sender_password)
    server.send_message(msg, to_addrs=recipients)
    server.quit()
    return True
  except Exception as e:
    st.warning(f"⚠️ メール送信に失敗しました: {e}")
    return False


# ==========================================
# 🚀 アプリメイン処理
# ==========================================
if "booking_step" not in st.session_state:
  st.session_state["booking_step"] = 1

# ------------------------------------------
# ステップ 1: 予約入力画面
# ------------------------------------------
if st.session_state["booking_step"] == 1:

  st.markdown(
      """
        <style>
        .header-container {
            background-color: #f8f9fa;
            padding: 16px 18px;
            border-radius: 12px;
            border-left: 5px solid #4A90E2;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        }
        .main-title {
            font-size: 1.35rem !important;
            font-weight: 800;
            color: #2C3E50;
            margin: 0 0 6px 0;
            line-height: 1.3;
        }
        .sub-title {
            font-size: 0.85rem;
            font-weight: bold;
            color: #4A90E2;
            background: #EBF3FA;
            display: inline-block;
            padding: 3px 10px;
            border-radius: 20px;
        }
        .desc-text {
            font-size: 0.88rem;
            color: #555;
            margin-top: 10px;
            line-height: 1.5;
        }
        </style>
        
        <div class="header-container">
            <div class="main-title">折り紙体験ワークショップ</div>
            <div class="sub-title">📝 参加予約フォーム</div>
            <div class="desc-text">
                ご希望の日時を選択し、必要事項を入力の上「予約を確定する」を押してください。
            </div>
        </div>
    """,
      unsafe_allow_html=True,
  )

  st.info("""
📍 **開催日程・場所・内容**
* **8月24日（14:00〜 / 18:00〜）**
  * 場所：スターバックス インターパークスタジアム店
  * 内容：折り紙でお花づくりワークショップ
* **8月25日（14:00〜 / 18:00〜）**
  * 場所：スターバックス FKD店
  * 内容：折り紙ランタン制作ワークショップ
""")

  dates_options = [
      "8月24日 14:00〜（折り紙でお花づくり）",
      "8月24日 18:00〜（折り紙でお花づくり）",
      "8月25日 14:00〜（折り紙ランタン制作）",
      "8月25日 18:00〜（折り紙ランタン制作）",
  ]

  selected_dates = st.multiselect(
      "参加希望日時を選んでください（複数選択できます）*",
      options=dates_options,
  )

  st.markdown("---")

  with st.form("booking_form"):
    st.subheader("参加者情報の入力")
    name = st.text_input("お名前（フルネーム）*", placeholder="例: 山田 太郎")
    email = st.text_input(
        "メールアドレス*", placeholder="例: example@email.com"
    )
    phone = st.text_input(
        "電話番号*", placeholder="例: 09012345678（ハイフンなし）"
    )

    num_people = st.selectbox(
        "参加人数*",
        options=[
            "1名",
            "2名",
            "3名",
            "4名",
            "5名以上（備考欄にご記入ください）",
        ],
    )

    source = st.selectbox(
        "このイベントをどこで知りましたか？",
        options=[
            "SNS（Instagram/X等）",
            "知人・友人の紹介",
            "チラシ・ポスター",
            "その他",
        ],
    )

    note = st.text_area(
        "ご質問・ご要望（任意）",
        placeholder=(
            "配慮事項や、複数人でお越しの際のご連絡などがあればご記入ください"
        ),
    )

    st.markdown("---")
    st.markdown(
        "**※イベント当日は様子を写真・動画撮影し、SNS等に掲載させていただく場合がございます。**"
    )
    agree = st.checkbox(
        "【注意事項】当日の写真撮影・SNS掲載、および前日までのキャンセルについて同意して予約します。*"
    )

    submit_button = st.form_submit_button("予約を確定する")

  if submit_button:
    if not selected_dates:
      st.warning("⚠️ 参加希望日時を少なくとも1つ選択してください。")
    elif not name or not email or not phone:
      st.warning("⚠️ お名前、メールアドレス、電話番号は必須項目です。")
    elif "@" not in email or "." not in email:
      st.warning("⚠️ 有効なメールアドレスの形式で入力してください。")
    elif not agree:
      st.warning(
          "⚠️ 予約を確定するには「注意事項」への同意チェックが必要です。"
      )
    else:
      try:
        ws = get_worksheet()

        dates_formatted = "\n".join(selected_dates)

        ws.append_row([
            name,
            email,
            phone,
            num_people,
            source,
            dates_formatted,
            note,
            "確定",
        ])

        subject = "【予約完了】折り紙体験ワークショップの予約を受け付けました"
        body = f"""{name} 様

この度は「折り紙体験ワークショップ」にお申し込みいただき、誠にありがとうございます。
以下の内容でご予約を承りました。

----------------------------------------
■ ご予約日時・内容：
{dates_formatted}

■ ご予約人数（各回）：{num_people}
----------------------------------------

【キャンセルのお手続きについて】
万が一キャンセルされる場合は、以下のキャンセル専用サイトよりお手続きをお願いいたします。
👉 {CANCEL_APP_URL}

【お問い合わせ】
ご不明な点がございましたら、以下のアドレスまでご連絡ください。
お問い合わせ先：{CONTACT_EMAIL}

当日のご参加を心よりお待ちしております。
"""
        send_email(email, subject, body)

        st.session_state["complete_name"] = name
        st.session_state["complete_num_people"] = num_people
        st.session_state["complete_dates_list"] = selected_dates
        st.session_state["complete_email"] = email
        st.session_state["booking_step"] = 2
        st.cache_resource.clear()
        st.rerun()

      except Exception as e:
        st.error(f"⚠️ 保存エラーが発生しました: {e}")

# ------------------------------------------
# ステップ 2: 予約完了画面
# ------------------------------------------
elif st.session_state["booking_step"] == 2:

  # 画面左下から右上へと飛び立つ大量のアニメーションを発火
  trigger_origami_crane_animation()

  st.success(
      f"🎉 {st.session_state['complete_name']}"
      f" 様（{st.session_state['complete_num_people']}）、ご予約が完了しました！"
  )

  st.info(
      f"✉️ ご予約確認メールを **{st.session_state['complete_email']}**"
      f" へ送信しました。ご質問等は {CONTACT_EMAIL} までお問い合わせください。"
  )

  st.markdown("---")
  st.subheader("📋 ご予約内容")
  st.write(f"**お名前:** {st.session_state['complete_name']} 様")
  st.write(f"**参加人数:** {st.session_state['complete_num_people']}")

  st.write("**確定日時:**")
  for d in st.session_state.get("complete_dates_list", []):
    st.write(f"・ {d}")

  st.markdown("---")

  if st.button("← 続けて別の予約をする"):
    st.session_state["booking_step"] = 1
    st.rerun()
