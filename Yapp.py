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
  """シラサギの群れ飛翔 ＋ 和風紙吹雪（コンフェッティ）の祝福アニメーション"""
  js_code = f"""
    <script>
    (function() {{
        let doc = window.parent.document;
        
        let oldElem = doc.getElementById('crane-anim-layer');
        if (oldElem) {{ oldElem.remove(); }}

        let style = doc.createElement('style');
        style.textContent = `
            .crane-svg-defs {{
                position: absolute !important;
                width: 0 !important;
                height: 0 !important;
                overflow: hidden !important;
                opacity: 0 !important;
                pointer-events: none !important;
            }}

            /* シラサギの飛翔アニメーション */
            @keyframes flyDiagonalCorrect {{
                0% {{
                    transform: translate(-10vw, 85vh) scale(0.65) rotate(25deg);
                    opacity: 0;
                }}
                15% {{ opacity: 1; }}
                45% {{
                    transform: translate(35vw, 42vh) scale(0.95) rotate(22deg);
                    opacity: 1;
                }}
                85% {{ opacity: 0.95; }}
                100% {{
                    transform: translate(115vw, -20vh) scale(1.2) rotate(18deg);
                    opacity: 0;
                }}
            }}

            @keyframes wingFlapReal {{
                0%, 100% {{ transform: rotate(0deg) scaleY(1); }}
                50% {{ transform: rotate(-30deg) scaleY(0.55); }}
            }}

            /* 和風紙吹雪の落下アニメーション */
            @keyframes confettiFall {{
                0% {{
                    transform: translateY(-50px) rotate(0deg) scale(1);
                    opacity: 1;
                }}
                80% {{ opacity: 0.9; }}
                100% {{
                    transform: translateY(105vh) rotate(720deg) scale(0.6);
                    opacity: 0;
                }}
            }}

            .crane-anim-container {{
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                width: 100vw !important;
                height: 100vh !important;
                pointer-events: none !important;
                z-index: 9999999 !important;
                overflow: hidden !important;
            }}

            .egret-bird {{
                position: absolute;
                top: 0;
                left: 0;
                width: 95px;
                height: 95px;
                animation: flyDiagonalCorrect 3.5s cubic-bezier(0.25, 0.1, 0.25, 1) forwards;
            }}

            .egret-wing-part {{
                transform-origin: 35% 50%;
                animation: wingFlapReal 0.22
