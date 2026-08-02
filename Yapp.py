import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import uuid

from google.oauth2.service_account import Credentials
import gspread
import streamlit as st

# ==========================================
# ⚙️ 基本設定 & 定数
# ==========================================
st.set_page_config(
    page_title="折り紙体験ワークショップ 予約フォーム",
    page_icon="🎨",
    layout="centered",
)

SPREADSHEET_NAME = "イベント予約一覧"
CONTACT_EMAIL = "aonisai0111@gmail.com"
ADMIN_EMAIL = "aonisai0111@gmail.com"
CANCEL_APP_URL = "https://djks33sfzskwjzeam4mbcr.streamlit.app/"

# 開催日時 & 店舗リスト
EVENT_SCHEDULES = [
    {
        "date": "8月24日（土）18:00〜",
        "place": "スターバックス インターパークスタジアム店",
        "title": "折り紙でお花づくり",
        "map": "https://maps.google.com/?q=スターバックス+インターパークスタジアム店",
    },
    {
        "date": "8月25日（日）14:00〜",
        "place": "スターバックス FKD店",
        "title": "折り紙ランタン制作",
        "map": "https://maps.google.com/?q=スターバックス+FKD宇都宮店",
    },
]


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


def send_reservation_email(to_email, name, selected_dates, num_people):
  try:
    sender_email = st.secrets["smtp"]["email"]
    sender_password = st.secrets["smtp"]["password"]

    msg = MIMEMultipart("alternative")
    msg["From"] = f"イベント事務局 <{sender_email}>"
    msg["To"] = to_email
    msg["Reply-To"] = CONTACT_EMAIL
    msg["Subject"] = "【予約完了】折り紙体験ワークショップのご予約ありがとうございます"

    # 日時リストのHTML化
    dates_html = "<br>".join([f"・ {d}" for d in selected_dates])

    # Gmail等の自動折りたたみ（引用文扱い）を防止するための動的ユニークID
    unique_ref = str(uuid.uuid4())[:8]

    body_html = f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; line-height: 1.6; color: #333333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <p>{name} 様</p>
    <p>このたびは「折り紙体験ワークショップ」にお申し込みいただき、誠にありがとうございます。<br>以下の内容でご予約を承りました。</p>
    
    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin: 20px 0;">
        <h3 style="margin-top:0; color: #1e293b; border-bottom: 2px solid #3b82f6; padding-bottom: 5px;">■ ご予約内容</h3>
        <p style="font-size: 15px; line-height: 1.8;">
            <strong>【ご予約日時・会場】</strong><br>
            {dates_html}
        </p>
        <p style="font-size: 15px; margin-bottom: 0;">
            <strong>【ご予約人数】</strong>：{num_people} 名
        </p>
    </div>

    <div style="background-color: #fff8f1; border: 1px solid #ffedd5; border-radius: 8px; padding: 15px; margin: 20px 0;">
        <h3 style="margin-top:0; color: #9a3412; border-bottom: 2px solid #f97316; padding-bottom: 5px;">【キャンセルのお手続きについて】</h3>
        <p style="margin-bottom: 0; color: #431407;">
            万が一キャンセルされる場合は、以下のキャンセル専用サイトよりお手続きをお願いいたします。<br>
            👉 <a href="{CANCEL_APP_URL}" style="color: #2563eb; font-weight: bold;">{CANCEL_APP_URL}</a>
        </p>
    </div>

    <div style="margin-top: 25px;">
        <h3 style="margin-top:0; color: #1e293b;">【お問い合わせ】</h3>
        <p style="color: #475569;">
            ご不明な点がございましたら、以下のアドレスまでご連絡ください。<br>
            お問い合わせ先：<a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>
        </p>
    </div>

    <p style="margin-top: 30px; font-weight: bold; color: #1e293b;">当日のご参加を心よりお待ちしております。</p>

    <!-- Gmailの自動折りたたみ防止用ダミーID（非表示） -->
    <div style="display:none !important; visibility:hidden; opacity:0; color:transparent; height:0; width:0; font-size:0px;">
        Ref-ID: {unique_ref}
    </div>
</body>
</html>
"""
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
# 🎨 見栄え用カスタムCSS
# ==========================================
st.markdown(
    """
<style>
.main-header {
    background-color: #EFF6FF;
    padding: 16px 20px;
    border-radius: 12px;
    border-left: 6px solid #3B82F6;
    margin-bottom: 24px;
}
.main-title {
    font-size: 1.35rem !important;
    font-weight: 800;
    color: #1E40AF;
    margin: 0;
}
</style>
<div class="main-header">
    <div class="main-title">🎨 折り紙体験ワークショップ 予約受付</div>
</div>
""",
    unsafe_allow_html=True,
)

# ステップ管理
if "reserve_step" not in st.session_state:
  st.session_state["reserve_step"] = 1


# ==========================================
# 🚀 ページ 1: 予約入力フォーム
# ==========================================
if st.session_state["reserve_step"] == 1:

  with st.form("reservation_form"):
    st.subheader("👤 お客様情報の入力")
    user_name = st.text_input(
        "お名前", placeholder="例: 山田 太郎", key="input_name"
    )
    user_email = st.text_input(
        "メールアドレス", placeholder="例: example@email.com", key="input_email"
    )
    num_people = st.selectbox("ご予約人数（各回）", options=[1, 2, 3, 4, 5], index=0)

    st.write("---")
    st.subheader("🗓️ 参加日時の選択")
    st.write("ご希望の日時にチェックを入れてください（複数選択可能）。")

    selected_schedules = []

    # 選択肢を綺麗にカード枠で包んで表示
    for idx, item in enumerate(EVENT_SCHEDULES):
      short_label = f"{item['date']} {item['place']}（{item['title']}）"
      with st.container(border=True):
        cb = st.checkbox(f"🗓️ {short_label}", key=f"sch_{idx}")
        if cb:
          selected_schedules.append(short_label)

    st.write("")
    submit_btn = st.form_submit_button(
        "予約内容を確認して送信する", use_container_width=True
    )

  if submit_btn:
    if not user_name.strip():
      st.warning("⚠️ お名前を入力してください。")
    elif not user_email.strip():
      st.warning("⚠️ メールアドレスを入力してください。")
    elif not selected_schedules:
      st.warning("⚠️ 参加希望日時を少なくとも1つ選択してください。")
    else:
      try:
        ws = get_worksheet()

        # スプレッドシートへ追加登録
        dates_str = "\n".join(selected_schedules)
        new_row = [
            user_name.strip(),
            user_email.strip(),
            "",  # 電話番号欄等（必要に応じて）
            "",
            "",
            dates_str,
            f"{num_people}名",
            "予約確定",
        ]
        ws.append_row(new_row)

        # 予約確定メール送信
        send_reservation_email(
            user_email.strip(), user_name.strip(), selected_schedules, num_people
        )

        st.session_state["res_name"] = user_name.strip()
        st.session_state["res_email"] = user_email.strip()
        st.session_state["res_dates"] = selected_schedules
        st.session_state["res_people"] = num_people
        st.session_state["reserve_step"] = 2
        st.cache_resource.clear()
        st.rerun()

      except Exception as e:
        st.error(f"⚠️ 予約処理中にエラーが発生しました: {e}")


# ==========================================
# 🚀 ページ 2: 予約完了画面
# ==========================================
elif st.session_state["reserve_step"] == 2:

  st.success("🎉 ご予約が完了いたしました！")

  st.write(f"### 📋 ご予約内容（{st.session_state['res_name']} 様）")

  for d in st.session_state.get("res_dates", []):
    st.write(f"・ {d}")

  st.write(f"**人数**：{st.session_state.get('res_people', 1)} 名")

  st.info(
      f"✉️ **{st.session_state['res_email']}**"
      " へ予約確認メールを送信いたしました。\nメール内のリンクよりいつでもキャンセル手続きが可能です。"
  )

  st.write("")
  if st.button("新しい予約を入力する"):
    st.session_state["reserve_step"] = 1
    st.rerun()
