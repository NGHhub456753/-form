import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import urllib.parse

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

# 📍 Googleマップ検索URL（店舗用）
MAP_URL_INTERPARK = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote("スターバックス インターパークスタジアム店")
MAP_URL_FKD = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote("スターバックス FKD店")


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
