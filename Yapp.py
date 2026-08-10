import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re
import uuid

from google.oauth2.service_account import Credentials
import gspread
import streamlit as st

# ==========================================
# ⚙️ 基本設定 & 定数
# ==========================================
st.set_page_config(
    page_title="折り紙体験ワークショップ 予約手続き",
    page_icon="📝",
    layout="centered",
)

SPREADSHEET_NAME = "イベント予約一覧"
CONTACT_EMAIL = "aonisai0111@gmail.com"
ADMIN_EMAIL = "aonisai0111@gmail.com"
CANCEL_APP_URL = "https://djks33sfzskwjzeam4mbcr.streamlit.app/"

# Googleマップ URL定義
MAP_URL_STAGE = (
    "https://maps.app.goo.gl/HH1EytAvCpih6sbaA"  # スタバ ステージ店（インターパーク）
)
MAP_URL_FKD = "https://maps.app.goo.gl/yY55vV7HQcb4yHxV7"  # スタバ FKD店

# 選択肢定義
SLOTS = [
    "8月24日（月）15:00〜 スターバックス インターパークスタジアム店",
    "8月24日（月）16:00〜 スターバックス インターパークスタジアム店",
    "8月24日（月）18:00〜 スターバックス インターパークスタジアム店",
    "8月25日（火）15:00〜 スターバックス FKD店（折り紙ランタン制作）",
    "8月25日（火）16:00〜 スターバックス FKD店（折り紙ランタン制作）",
    "8月25日（火）18:00〜 スターバックス FKD店（折り紙ランタン制作）",
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


def shorten_date_str(text):
  text = text.replace("スターバックス インターパークスタジアム店", "スタバ ステージ店")
  text = text.replace("スターバックスインターパークスタジアム店", "スタバ ステージ店")
  text = text.replace("スターバックス FKD店", "スタバ FKD店")
  text = text.replace("スターバックスFKD店", "スタバ FKD店")
  return text


def format_date_with_map_link(text):
  shortened = shorten_date_str(text)

  if "スタバ ステージ店" in shortened:
    link_html = f'<a href="{MAP_URL_STAGE}" target="_blank" style="color: #2563eb; text-decoration: underline; font-weight: bold;">スタバ ステージ店</a>'
    shortened = shortened.replace("スタバ ステージ店", link_html)

  elif "スタバ FKD店" in shortened:
    link_html = f'<a href="{MAP_URL_FKD}" target="_blank" style="color: #2563eb; text-decoration: underline; font-weight: bold;">スタバ FKD店</a>'
    shortened = shortened.replace("スタバ FKD店", link_html)

  return shortened


def send_booking_email(
    to_email, name, phone, num_people, source, note, selected_dates
):
  try:
    sender_email = st.secrets["smtp"]["email"]
    sender_password = st.secrets["smtp"]["password"]

    msg = MIMEMultipart("alternative")
    msg["From"] = f"イベント事務局 <{sender_email}>"
    msg["To"] = to_email
    msg["Reply-To"] = CONTACT_EMAIL
    msg["Subject"] = "【予約受付】折り紙体験ワークショップのご予約"

    dates_html = "<br>".join(
        [f"・ {format_date_with_map_link(d)}" for d in selected_dates]
    )

    note_html = (
        f"<p style='margin-bottom:0;'><b>ご質問・ご要望：</b><br>{note}</p>"
        if note
        else ""
    )
    unique_ref = str(uuid.uuid4())[:8]

    body_html = f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; line-height: 1.6; color: #333333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <p>{name} 様</p>
    <p>「折り紙体験ワークショップ」へのお申し込みを受け付けいたしました。</p>
    
    <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 15px; margin: 20px 0;">
        <h3 style="margin-top:0; color: #991b1b; border-bottom: 2px solid #f87171; padding-bottom: 5px;">■ ご予約日時</h3>
        <p style="font-size: 15px; line-height: 1.8; color: #7f1d1d; margin-bottom: 0;">
            {dates_html}
        </p>
    </div>

    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin: 20px 0;">
        <h3 style="margin-top:0; color: #334155; border-bottom: 2px solid #cbd5e1; padding-bottom: 5px;">■ お申し込み内容</h3>
        <p style="margin-bottom: 5px;"><b>お名前：</b> {name} 様</p>
        <p style="margin-bottom: 5px;"><b>電話番号：</b> {phone}</p>
        <p style="margin-bottom: 5px;"><b>参加人数：</b> {num_people}</p>
        <p style="margin-bottom: 5px;"><b>認知きっかけ：</b> {source}</p>
        {note_html}
    </div>

    <p style="margin-top: 25px;">当日のご参加を心よりお待ちしております。</p>
    
    <hr style="border: none; border-top: 1px dashed #cbd5e1; margin: 25px 0;">
    <p style="font-size: 13px; color: #64748b;">
        ご都合が悪くなった場合は、以下の専用ページよりキャンセル手続きを行っていただけます。<br>
        キャンセルページ：<a href="{CANCEL_APP_URL}">{CANCEL_APP_URL}</a><br><br>
        ご不明な点がございましたら以下までご連絡ください。<br>
        お問い合わせ先：<a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>
    </p>

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
# 🎨 見栄え用カスタムCSS & 不要UI非表示
# ==========================================
st.markdown(
    """
<style>
/* ⚙️ Manage app ボタンや不要なフッター/ヘッダーを完全に非表示 */
[data-testid="stStatusWidget"],
[data-testid="stViewerBadge"],
[data-testid="manage-app-button"],
.stAppViewerToolBar,
#MainMenu,
footer,
header {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    height: 0 !important;
    width: 0 !important;
    pointer-events: none !important;
}

.cancel-header {
    background-color: #FEF2F2;
    padding: 16px 20px;
    border-radius: 12px;
    border-left: 6px solid #EF4444;
    margin-bottom: 24px;
}
.cancel-title {
    font-size: 1.35rem !important;
    font-weight: 800;
    color: #991B1B;
    margin: 0;
}
</style>
<div class="cancel-header">
    <div class="cancel-title">📝 ご予約手続き</div>
</div>
""",
    unsafe_allow_html=True,
)

if "booking_step" not in st.session_state:
  st.session_state["booking_step"] = 1


# ==========================================
# 🚀 ページ 1: 情報入力画面
# ==========================================
if st.session_state["booking_step"] == 1:

  st.markdown("### 📋 ご予約情報の入力")
  st.write("必要事項を入力し、参加を希望する日時を選択してください。")

  with st.form("booking_input_form"):
    name = st.text_input("お名前（フルネーム）*", placeholder="例: 山田 太郎")
    email = st.text_input("メールアドレス*", placeholder="例: example@email.com")
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

    st.write("---")
    st.markdown("### 🗓️ 参加希望日時の選択（複数選択可）*")

    selected_dates = []
    for idx, slot in enumerate(SLOTS):
      short_text = shorten_date_str(slot)
      with st.container(border=True):
        cb = st.checkbox(f"🗓️  {short_text}", key=f"slot_{idx}")
        if cb:
          selected_dates.append(slot)

    st.write("")
    agree = st.checkbox(
        "【同意確認】キャンセル方法および当日の撮影について確認し、同意の上で予約します。*"
    )

    st.write("")
    submit_btn = st.form_submit_button("予約を確定する", use_container_width=True)

  if submit_btn:
    email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"

    if not name.strip():
      st.warning("⚠️ お名前を入力してください。")
    elif not email.strip() or not re.match(email_pattern, email.strip()):
      st.warning("⚠️ 正しいメールアドレスを入力してください。")
    elif not selected_dates:
      st.warning("⚠️ 参加希望日時を少なくとも1つ選択してください。")
    elif not agree:
      st.warning(
          "⚠️ 予約を確定するには「同意確認」のチェックが必要です。"
      )
    else:
      try:
        ws = get_worksheet()

        dates_str = "\n".join(selected_dates)
        phone_save = phone.strip() if phone.strip() else "未入力"

        ws.append_row([
            name.strip(),
            email.strip(),
            phone_save,
            num_people,
            source,
            dates_str,
            note.strip(),
            "確定",
        ])

        send_booking_email(
            email.strip(),
            name.strip(),
            phone_save,
            num_people,
            source,
            note.strip(),
            selected_dates,
        )

        st.session_state["complete_name"] = name.strip()
        st.session_state["complete_email"] = email.strip()
        st.session_state["complete_dates"] = selected_dates
        st.session_state["booking_step"] = 2
        st.cache_resource.clear()
        st.rerun()

      except Exception as e:
        st.error(f"⚠️ 予約処理中にエラーが発生しました: {e}")


# ==========================================
# 🚀 ページ 2: 予約完了画面
# ==========================================
elif st.session_state["booking_step"] == 2:

  st.success("✅ ご予約の手続きが完了いたしました。")

  with st.container(border=True):
    st.markdown("### 📄 ご予約内容")
    st.write(f"**お名前:** {st.session_state.get('complete_name')} 様")
    st.write("")
    st.markdown("**■ ご予約日時**")
    for d in st.session_state.get("complete_dates", []):
      st.write(f"・ {shorten_date_str(d)}")

  st.write("")
  st.write(
      f"✉️ **{st.session_state.get('complete_email')}**"
      " へ完了メールを送信いたしました。"
  )

  st.write("")
  if st.button("トップ画面に戻る", use_container_width=True):
    st.session_state["booking_step"] = 1
    st.rerun()
