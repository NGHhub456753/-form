import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.service_account import Credentials
import gspread
import pandas as pd
import streamlit as st

# --- ページ設定 ---
st.set_page_config(
    page_title="折り紙体験ワークショップ 参加予約", page_icon="📝"
)

SPREADSHEET_NAME = "イベント予約一覧"  # Googleスプレッドシートのファイル名

# ★ 明日新しいアドレスが決まったらここを変更してください
CONTACT_EMAIL = "hanaizu64@gmail.com"  # お問い合わせ先アドレス
ADMIN_EMAIL = "hanaizu64@gmail.com"  # 管理者（自分）のアドレス

# ★ キャンセルアプリのURL
CANCEL_APP_URL = "https://djks33sfzskwjzeam4mbcr.streamlit.app/"


# --- Google Sheets 接続関数 ---
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


# --- メール送信関数（予約者＋管理者＋お問い合わせ先の全宛先に送信） ---
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

    # 重複して届かないよう set でユニーク化して送信先リストを作成
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


# セッション状態の初期化
if "booking_step" not in st.session_state:
  st.session_state["booking_step"] = 1

# スマホ調整CSS付きタイトル
st.markdown(
    """
    <style>
    .custom-title {
        font-size: 1.6rem !important;
        font-weight: bold;
        margin-bottom: 0.5rem;
        word-break: keep-all;
        white-space: nowrap;
    }
    </style>
    <h1 class="custom-title">折り紙体験ワークショップ 参加予約</h1>
""",
    unsafe_allow_html=True,
)

# ==========================================
# ステップ 1: 予約入力画面
# ==========================================
if st.session_state["booking_step"] == 1:
  st.write(
      "ご希望の日時（複数選択可）を選択し、必要事項を入力して「予約を確定する」を押してください。"
  )

  # イベント開催概要の表示
  st.info("""
📍 **開催日程・場所・内容**
* **8月24日（14:00〜 / 18:00〜）**
  * 場所：スターバックス インターパークスタジアム店
  * 内容：折り紙でお花づくりワークショップ
* **8月25日（14:00〜 / 18:00〜）**
  * 場所: スターバックスFKD店
  * 内容：折り紙ランタン制作ワークショップ
""")

  # スマホで見やすく「折り紙」を入れた選択肢
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
        "※イベント当日は様子を写真・動画撮影し、SNS等に掲載させていただく場合がございます。"
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

        dates_formatted = "、\n".join(selected_dates)
        dates_single_line = "、".join(selected_dates)

        # スプレッドシートに保存
        ws.append_row([
            name,
            email,
            phone,
            num_people,
            source,
            dates_single_line,
            note,
            "確定",
        ])

        # 確認メール送信
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

        # 完了画面へ切り替え
        st.session_state["complete_name"] = name
        st.session_state["complete_num_people"] = num_people
        st.session_state["complete_dates"] = dates_single_line
        st.session_state["complete_email"] = email
        st.session_state["booking_step"] = 2
        st.cache_resource.clear()
        st.rerun()

      except Exception as e:
        st.error(f"⚠️ 保存エラーが発生しました: {e}")

# ==========================================
# ステップ 2: 予約完了画面
# ==========================================
elif st.session_state["booking_step"] == 2:
  st.balloons()

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
  st.write(f"**確定日時:** {st.session_state['complete_dates']}")
  st.markdown("---")

  if st.button("← 続けて別の予約をする"):
    st.session_state["booking_step"] = 1
    st.rerun()
