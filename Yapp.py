import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import uuid

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

# 📍 Googleマップ共有URL（指定リンク）
MAP_URL_INTERPARK = "https://maps.app.goo.gl/HH1EytAvCpih6sbaA"
MAP_URL_FKD = "https://maps.app.goo.gl/yY55vV7HQcb4yHxV7"


# ==========================================
# 🎨 アニメーション・デザイン専用ブロック
# ==========================================
def trigger_origami_crane_animation():
  """シラサギの群れ飛翔 ＋ 和風紙吹雪（コンフェッティ）の祝福アニメーション"""
  js_code = """
    <script>
    (function() {
        let doc = window.parent.document;
        
        let oldElem = doc.getElementById('crane-anim-layer');
        if (oldElem) { oldElem.remove(); }

        let style = doc.createElement('style');
        style.textContent = `
            .crane-svg-defs {
                position: absolute !important;
                width: 0 !important;
                height: 0 !important;
                overflow: hidden !important;
                opacity: 0 !important;
                pointer-events: none !important;
            }

            /* シラサギの飛翔アニメーション */
            @keyframes flyDiagonalCorrect {
                0% {
                    transform: translate(-10vw, 85vh) scale(0.65) rotate(25deg);
                    opacity: 0;
                }
                15% { opacity: 1; }
                45% {
                    transform: translate(35vw, 42vh) scale(0.95) rotate(22deg);
                    opacity: 1;
                }
                85% { opacity: 0.95; }
                100% {
                    transform: translate(115vw, -20vh) scale(1.2) rotate(18deg);
                    opacity: 0;
                }
            }

            @keyframes wingFlapReal {
                0%, 100% { transform: rotate(0deg) scaleY(1); }
                50% { transform: rotate(-30deg) scaleY(0.55); }
            }

            /* 和風紙吹雪の落下アニメーション */
            @keyframes confettiFall {
                0% {
                    transform: translateY(-50px) rotate(0deg) scale(1);
                    opacity: 1;
                }
                80% { opacity: 0.9; }
                100% {
                    transform: translateY(105vh) rotate(720deg) scale(0.6);
                    opacity: 0;
                }
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
                width: 95px;
                height: 95px;
                animation: flyDiagonalCorrect 3.5s cubic-bezier(0.25, 0.1, 0.25, 1) forwards;
            }

            .egret-wing-part {
                transform-origin: 35% 50%;
                animation: wingFlapReal 0.22s infinite ease-in-out;
            }

            .confetti-piece {
                position: absolute;
                top: -20px;
                width: 12px;
                height: 14px;
                opacity: 0;
                animation: confettiFall 4.2s linear forwards;
            }
        `;
        doc.head.appendChild(style);

        let container = doc.createElement('div');
        container.id = 'crane-anim-layer';
        container.className = 'crane-anim-container';
        
        let svgShape = `
            <svg class="crane-svg-defs" aria-hidden="true">
                <defs>
                    <g id="real-egret-shape">
                        <polygon points="15,65 35,55 50,58 30,75" fill="#CBD5E1"/>
                        <polygon points="35,55 55,45 60,52 50,58" fill="#FFFFFF"/>
                        <polygon points="55,45 78,25 82,28 60,52" fill="#F8FAFC"/>
                        <polygon points="78,25 95,20 82,28" fill="#FFA500"/>
                        <circle cx="76" cy="24" r="1.5" fill="#1E293B"/>
                        <g class="egret-wing-part">
                            <polygon points="40,52 65,8 60,48" fill="#FFFFFF"/>
                            <polygon points="60,48 65,8 75,40" fill="#E2E8F0"/>
                        </g>
                    </g>
                </defs>
            </svg>
        `;

        // 10羽のシラサギ
        let birdsHTML = '';
        let delays = [0, 0.2, 0.4, 0.65, 0.85, 1.1, 1.3, 1.55, 1.8, 2.0];
        let offsets = [
            {x: '-5vw', y: '5vh', s: 1.0},
            {x: '-12vw', y: '12vh', s: 0.85},
            {x: '-3vw', y: '20vh', s: 1.1},
            {x: '-10vw', y: '28vh', s: 0.9},
            {x: '-16vw', y: '18vh', s: 0.75},
            {x: '-6vw', y: '8vh', s: 0.95},
            {x: '-14vw', y: '24vh', s: 0.8},
            {x: '-4vw', y: '32vh', s: 1.05},
            {x: '-11vw', y: '15vh', s: 0.88},
            {x: '-8vw', y: '22vh', s: 0.92}
        ];

        for(let i = 0; i < delays.length; i++) {
            birdsHTML += `<div class="egret-bird" style="margin-left: ${offsets[i].x}; margin-top: ${offsets[i].y}; animation-delay: ${delays[i]}s; transform: scale(${offsets[i].s});"><svg viewBox="0 0 100 100"><use href="#real-egret-shape"/></svg></div>`;
        }

        // 和風紙吹雪
        let confettiHTML = '';
        let colors = ['#FFD700', '#E63946', '#4A90E2', '#FFFFFF', '#F4A261', '#2A9D8F'];
        for(let j = 0; j < 35; j++) {
            let left = Math.random() * 100;
            let delay = Math.random() * 2.2;
            let bg = colors[Math.floor(Math.random() * colors.length)];
            let scale = 0.6 + Math.random() * 0.8;
            confettiHTML += `<div class="confetti-piece" style="left: ${left}vw; animation-delay: ${delay}s; background-color: ${bg}; transform: scale(${scale}); clip-path: polygon(10% 0%, 100% 20%, 85% 100%, 0% 80%);"></div>`;
        }

        container.innerHTML = svgShape + birdsHTML + confettiHTML;
        doc.body.appendChild(container);

        setTimeout(() => {
            if (container) container.remove();
        }, 6000);
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


def send_email(to_email, subject, body_html):
  try:
    sender_email = st.secrets["smtp"]["email"]
    sender_password = st.secrets["smtp"]["password"]

    msg = MIMEMultipart("alternative")
    msg["From"] = f"イベント事務局 <{sender_email}>"
    msg["To"] = to_email
    msg["Reply-To"] = CONTACT_EMAIL
    msg["Subject"] = subject

    # HTMLメールとして作成
    msg.attach(MIMEText(body_html, "html", "utf-8"))

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
      """<style>
.header-container {
    background-color: #f8f9fa;
    padding: 18px 20px;
    border-radius: 12px;
    border-left: 6px solid #4A90E2;
    margin-bottom: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.04);
}
.main-title {
    font-size: 1.5rem !important;
    font-weight: 800;
    color: #2C3E50;
    margin: 0 0 8px 0;
    line-height: 1.3;
}
.sub-title {
    font-size: 0.95rem;
    font-weight: bold;
    color: #4A90E2;
    background: #EBF3FA;
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
}
.desc-text {
    font-size: 1.0rem;
    color: #444;
    margin-top: 12px;
    line-height: 1.6;
}

/* Venue card header style */
.venue-header {
    background-color: #F1F5F9;
    border-left: 5px solid #0284C7;
    padding: 8px 12px;
    border-radius: 4px;
    font-weight: bold;
    font-size: 1.05rem;
    color: #0F172A;
    margin-top: 15px;
    margin-bottom: 8px;
}

/* 📌 注意事項・キャンセル方法の読みやすい枠 */
.notice-card {
    background-color: #F8FAFC;
    border: 2px solid #CBD5E1;
    border-radius: 10px;
    padding: 18px 20px;
    margin: 20px 0 15px 0;
    line-height: 1.7;
}
.notice-title {
    font-size: 1.15rem;
    font-weight: bold;
    color: #1E293B;
    margin-bottom: 12px;
    border-bottom: 1px dashed #94A3B8;
    padding-bottom: 6px;
}
.notice-section {
    margin-bottom: 12px;
    font-size: 1.0rem;
    color: #334155;
}
.notice-section-title {
    font-weight: bold;
    color: #0F172A;
    display: block;
    margin-bottom: 4px;
}
</style>

<div class="header-container">
    <div class="main-title">折り紙体験ワークショップ</div>
    <div class="sub-title">📝 参加予約フォーム</div>
    <div class="desc-text">
        ご希望の日時を選び、お名前とご連絡先を入力して「予約を確定する」ボタンを押してください。
    </div>
</div>
""",
      unsafe_allow_html=True,
  )

  with st.form("booking_form"):
    st.subheader("🗓️ 参加希望日時の選択（複数えらべます）*")

    # 📍 会場 1
    st.markdown(
        """<div class="venue-header">📍 スターバックス インターパークスタジアム店<br><small style="font-weight:normal; color:#475569;">内容：折り紙でお花づくり</small></div>""",
        unsafe_allow_html=True,
    )
    d1 = st.checkbox("8月24日（月）14:00〜")
    d2 = st.checkbox("8月24日（月）18:00〜")

    st.write("")

    # 📍 会場 2
    st.markdown(
        """<div class="venue-header">📍 スターバックス FKD店<br><small style="font-weight:normal; color:#475569;">内容：折り紙ランタン制作</small></div>""",
        unsafe_allow_html=True,
    )
    d3 = st.checkbox("8月25日（火）14:00〜")
    d4 = st.checkbox("8月25日（火）18:00〜")

    st.markdown("---")
    st.subheader("参加される方のお名前・ご連絡先")

    name = st.text_input("お名前（フルネーム）*", placeholder="例: 山田 太郎")

    email = st.text_input(
        "メールアドレス*", placeholder="例: example@email.com"
    )

    phone = st.text_input(
        "電話番号（任意）", placeholder="例: 09012345678（ハイフンなし）"
    )

    num_people = st.selectbox(
        "参加人数*",
        options=[
            "1名",
            "2名",
            "3名",
            "4名",
            "5名以上（下の備考欄にご記入ください）",
        ],
    )

    source = st.selectbox(
        "このイベントをどこで知りましたか？",
        options=[
            "SNS（Instagram / X など）",
            "知人・友人の紹介",
            "チラシ・ポスター",
            "その他",
        ],
    )

    note = st.text_area(
        "ご質問・ご要望（任意）",
        placeholder=(
            "お体への配慮や、複数人でお越しのご連絡などがあればご記入ください"
        ),
    )

    # 📌 高齢の方でも読みやすい注意事項カード
    notice_html = """<div class="notice-card">
<div class="notice-title">📌 ご予約のキャンセル・注意事項</div>
<div class="notice-section">
<span class="notice-section-title">【キャンセルの方法】</span>
万が一ご都合が悪くなった場合は、予約完了後にお送りする<b>「確認メール」の中にキャンセル用リンク</b>がございます。<br>そちらのリンクからいつでもお手続きいただけます。
</div>
<div class="notice-section" style="margin-bottom: 0;">
<span class="notice-section-title">【写真・動画の撮影について】</span>
当日はイベントの様子を撮影し、広報やSNS等に掲載させていただく場合がございます。あらかじめご了承ください。
</div>
</div>"""

    st.markdown(notice_html, unsafe_allow_html=True)

    agree = st.checkbox(
        "【同意確認】キャンセル方法および当日の撮影について確認し、同意の上で予約します。*"
    )

    submit_button = st.form_submit_button("予約を確定する")

  if submit_button:
    # 画面表示＆スプレッドシート用
    selected_dates_text = []
    # HTMLメール用（Googleマップリンク付き）
    selected_dates_html = []

    if d1:
      txt = "8月24日（月）14:00〜 スターバックス インターパークスタジアム店（折り紙でお花づくり）"
      html_item = f'8月24日（月）14:00〜 <a href="{MAP_URL_INTERPARK}" target="_blank" style="color: #0284C7; font-weight: bold; text-decoration: underline;">📍 スターバックス インターパークスタジアム店</a>（折り紙でお花づくり）'
      selected_dates_text.append(txt)
      selected_dates_html.append(html_item)

    if d2:
      txt = "8月24日（月）18:00〜 スターバックス インターパークスタジアム店（折り紙でお花づくり）"
      html_item = f'8月24日（月）18:00〜 <a href="{MAP_URL_INTERPARK}" target="_blank" style="color: #0284C7; font-weight: bold; text-decoration: underline;">📍 スターバックス インターパークスタジアム店</a>（折り紙でお花づくり）'
      selected_dates_text.append(txt)
      selected_dates_html.append(html_item)

    if d3:
      txt = "8月25日（火）14:00〜 スターバックス FKD店（折り紙ランタン制作）"
      html_item = f'8月25日（火）14:00〜 <a href="{MAP_URL_FKD}" target="_blank" style="color: #0284C7; font-weight: bold; text-decoration: underline;">📍 スターバックス FKD店</a>（折り紙ランタン制作）'
      selected_dates_text.append(txt)
      selected_dates_html.append(html_item)

    if d4:
      txt = "8月25日（火）18:00〜 スターバックス FKD店（折り紙ランタン制作）"
      html_item = f'8月25日（火）18:00〜 <a href="{MAP_URL_FKD}" target="_blank" style="color: #0284C7; font-weight: bold; text-decoration: underline;">📍 スターバックス FKD店</a>（折り紙ランタン制作）'
      selected_dates_text.append(txt)
      selected_dates_html.append(html_item)

    if not selected_dates_text:
      st.warning("⚠️ 参加希望日時を少なくとも1つ選択してください。")
    elif not name or not email:
      st.warning("⚠️ お名前とメールアドレスは必須項目です。")
    elif "@" not in email or "." not in email:
      st.warning("⚠️ 有効なメールアドレスの形式で入力してください。")
    elif not agree:
      st.warning(
          "⚠️ 予約を確定するには「同意確認」のチェックが必要です。"
      )
    else:
      try:
        ws = get_worksheet()

        dates_formatted_spreadsheet = "\n".join(selected_dates_text)
        phone_save = phone if phone else "未入力"

        ws.append_row([
            name,
            email,
            phone_save,
            num_people,
            source,
            dates_formatted_spreadsheet,
            note,
            "確定",
        ])

        subject = "【予約完了】折り紙体験ワークショップの予約を受け付けました"

        dates_html_body = "<br>".join(
            [f"・ {item}" for item in selected_dates_html]
        )

        # Gmail自動折りたたみ防止用ID
        unique_ref = str(uuid.uuid4())[:8]

        body_html = f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; line-height: 1.6; color: #333333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <p>{name} 様</p>
    <p>この度は「折り紙体験ワークショップ」にお申し込みいただき、誠にありがとうございます。<br>以下の内容でご予約を承りました。</p>
    
    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin: 20px 0;">
        <h3 style="margin-top:0; color: #0f172a; border-bottom: 2px solid #0284c7; padding-bottom: 5px;">■ ご予約日時・会場</h3>
        <p style="font-size: 15px; line-height: 1.8;">
            {dates_html_body}
        </p>
        <p style="font-size: 13px; color: #64748b; margin-top: 10px;">
            ※ 青文字の店名をタップすると<b>Googleマップ</b>で場所を確認できます。
        </p>
        <hr style="border: none; border-top: 1px dashed #cbd5e1; margin: 15px 0;">
        <p style="margin-bottom: 0;"><b>■ ご予約人数（各回）：</b> {num_people}</p>
    </div>

    <div style="margin: 25px 0;">
        <h4 style="margin-bottom: 5px; color: #0f172a;">【キャンセルのお手続きについて】</h4>
        <p style="margin-top: 0;">万が一キャンセルされる場合は、以下のキャンセル専用サイトよりお手続きをお願いいたします。<br>
        👉 <a href="{CANCEL_APP_URL}" style="color: #0284c7; font-weight: bold;">{CANCEL_APP_URL}</a></p>
    </div>

    <div style="margin: 25px 0;">
        <h4 style="margin-bottom: 5px; color: #0f172a;">【お問い合わせ】</h4>
        <p style="margin-top: 0;">ご不明な点がございましたら、以下のアドレスまでご連絡ください。<br>
        お問い合わせ先：<a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p>
    </div>

    <p style="margin-top: 30px;">当日のご参加を心よりお待ちしております。</p>

    <!-- Gmail自動折りたたみ防止用ダミーID -->
    <div style="display:none !important; visibility:hidden; opacity:0; color:transparent; height:0; width:0; font-size:0px;">
        Ref-ID: {unique_ref}
    </div>
</body>
</html>
"""
        send_email(email, subject, body_html)

        st.session_state["complete_name"] = name
        st.session_state["complete_num_people"] = num_people
        st.session_state["complete_dates_list"] = selected_dates_text
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

  # シラサギ＆紙吹雪アニメーションを発火
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

  st.write("**確定日時・会場:**")
  for d in st.session_state.get("complete_dates_list", []):
    st.write(f"・ {d}")

  st.markdown("---")

  if st.button("← 続けて別の予約をする"):
    st.session_state["booking_step"] = 1
    st.rerun()
