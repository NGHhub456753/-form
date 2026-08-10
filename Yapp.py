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
    page_title="折り紙体験ワークショップ 予約フォーム",
    page_icon="🌸",
    layout="centered",
)

SPREADSHEET_NAME = "イベント予約一覧"
CONTACT_EMAIL = "aonisai0111@gmail.com"
ADMIN_EMAIL = "aonisai0111@gmail.com"

# 各枠の上限人数（名）
CAPACITY_LIMIT = 6

# Googleマップ URL定義
MAP_URL_STAGE = (
    "https://maps.app.goo.gl/HH1EytAvCpih6sbaA"  # スタバ ステージ店（インターパーク）
)
MAP_URL_FKD = "https://maps.app.goo.gl/yY55vV7HQcb4yHxV7"  # スタバ FKD店

# 時間枠の定義 (内部ID: 表示名)
# 8月24日 18:00〜 のみ「ランタンづくり」
SLOTS = {
    "slot_1": (
        "8月24日（月）15:00〜16:00（スターバックス"
        " インターパークスタジアム店）★折り紙でお花づくり"
    ),
    "slot_2": (
        "8月24日（月）16:00〜17:00（スターバックス"
        " インターパークスタジアム店）★折り紙でお花づくり"
    ),
    "slot_3": (
        "8月24日（月）18:00〜19:00（スターバックス"
        " インターパークスタジアム店）★折り紙でランタンづくり"
    ),
    "slot_4": (
        "8月25日（火）15:00〜16:00（スターバックス"
        " FKD店）★折り紙でお花づくり"
    ),
    "slot_5": (
        "8月25日（火）16:00〜17:00（スターバックス"
        " FKD店）★折り紙でお花づくり"
    ),
    "slot_6": (
        "8月25日（火）18:00〜19:00（スターバックス"
        " FKD店）★折り紙でお花づくり"
    ),
}


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


def get_slot_counts():
  ws = get_worksheet()
  records = ws.get_all_values()

  counts = {k: 0 for k in SLOTS.keys()}

  if len(records) > 1:
    for row in records[1:]:
      if len(row) >= 8:
        dates_cell = row[5]
        status = row[7].strip()

        if status != "キャンセル" and dates_cell:
          selected_lines = dates_cell.split("\n")
          for slot_key, slot_name in SLOTS.items():
            for line in selected_lines:
              if slot_name in line:
                counts[slot_key] += 1
                break

  return counts


# 日時テキストを短く表示用に整形する関数
def shorten_date_str(text):
  text = text.replace("8月24日（土）", "8月24日（月）")
  text = text.replace("8月24日(土)", "8月24日（月）")
  text = text.replace("8月25日（日）", "8月25日（火）")
  text = text.replace("8月25日(日)", "8月25日（火）")

  text = text.replace("スターバックス インターパークスタジアム店", "スタバ ステージ店")
  text = text.replace("スターバックスインターパークスタジアム店", "スタバ ステージ店")
  text = text.replace("スターバックス FKD店", "スタバ FKD店")
  text = text.replace("スターバックスFKD店", "スタバ FKD店")

  text = text.replace("折り紙でお花づくり", "お花づくり")
  text = text.replace("折り紙でランタンづくり", "ランタンづくり")
  return text


# メール用に店舗名をマップリンク化する関数
def format_date_with_map_link(text):
  shortened = shorten_date_str(text)

  if "スタバ ステージ店" in shortened:
    link_html = f'<a href="{MAP_URL_STAGE}" target="_blank" style="color: #2563eb; text-decoration: underline; font-weight: bold;">スタバ ステージ店</a>'
    shortened = shortened.replace("スタバ ステージ店", link_html)

  elif "スタバ FKD店" in shortened:
    link_html = f'<a href="{MAP_URL_FKD}" target="_blank" style="color: #2563eb; text-decoration: underline; font-weight: bold;">スタバ FKD店</a>'
    shortened = shortened.replace("スタバ FKD店", link_html)

  return shortened


def send_confirmation_email(
    to_email, name, age, phone, comment, selected_slots_names
):
  try:
    sender_email = st.secrets["smtp"]["email"]
    sender_password = st.secrets["smtp"]["password"]

    msg = MIMEMultipart("alternative")
    msg["From"] = f"イベント事務局 <{sender_email}>"
    msg["To"] = to_email
    msg["Reply-To"] = CONTACT_EMAIL
    msg["Subject"] = "【予約完了】折り紙体験ワークショップのお申し込み"

    dates_html = "<br>".join(
        [f"・ {format_date_with_map_link(s)}" for s in selected_slots_names]
    )

    comment_html = (
        f"<p style='margin-bottom:0;'><b>ご質問・ご要望：</b><br>{comment}</p>"
        if comment
        else ""
    )

    unique_ref = str(uuid.uuid4())[:8]

    body_html = f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; line-height: 1.6; color: #333333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <p>{name} 様</p>
    <p>「折り紙体験ワークショップ」へのお申し込み、誠にありがとうございます。<br>以下の内容でご予約を受け付けいたしました。</p>
    
    <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 15px; margin: 20px 0;">
        <h3 style="margin-top:0; color: #166534; border-bottom: 2px solid #86efac; padding-bottom: 5px;">■ ご予約日時・会場</h3>
        <p style="font-size: 15px; line-height: 1.8; color: #14532d; margin-bottom: 0;">
            {dates_html}
        </p>
    </div>

    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin: 20px 0;">
        <h3 style="margin-top:0; color: #334155; border-bottom: 2px solid #cbd5e1; padding-bottom: 5px;">■ お客様情報</h3>
        <p style="margin-bottom: 5px;"><b>お名前：</b> {name} 様</p>
        <p style="margin-bottom: 5px;"><b>年齢：</b> {age} 歳</p>
        <p style="margin-bottom: 5px;"><b>電話番号：</b> {phone}</p>
        {comment_html}
    </div>

    <p style="margin-top: 25px;">当日のご参加を心よりお待ちしております。</p>
    
    <hr style="border: none; border-top: 1px dashed #cbd5e1; margin: 25px 0;">
    <p style="font-size: 13px; color: #64748b;">
        ご不明な点やミスの修正、予約キャンセルにつきましては以下までご連絡ください。<br>
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

.main-header {
    background-color: #FEF2F2;
    padding: 16px 20px;
    border-radius: 12px;
    border-left: 6px solid #EF4444;
    margin-bottom: 24px;
}
.main-title {
    font-size: 1.35rem !important;
    font-weight: 800;
    color: #991B1B;
    margin: 0;
}
</style>
<div class="main-header">
    <div class="main-title">🌸 折り紙体験ワークショップ 予約フォーム</div>
</div>
""",
    unsafe_allow_html=True,
)

if "page_step" not in st.session_state:
  st.session_state["page_step"] = 1


# リアルタイムの各枠の予約件数を取得
slot_counts = get_slot_counts()


# ==========================================
# 🚀 ページ 1: 入力フォーム
# ==========================================
if st.session_state["page_step"] == 1:

  st.markdown("### 🔍 参加日時の選択")
  st.write("ご希望の日時を選択し、必要事項をご入力のうえお申し込みください。")

  selected_slots = []

  with st.form("booking_form"):
    st.write("---")

    for slot_key, slot_name in SLOTS.items():
      current_count = slot_counts.get(slot_key, 0)
      rem_seats = CAPACITY_LIMIT - current_count
      is_full = rem_seats <= 0

      short_label = shorten_date_str(slot_name)

      with st.container(border=True):
        if is_full:
          st.checkbox(
              f"❌ {short_label}（満席）", disabled=True, key=slot_key
          )
        else:
          cb = st.checkbox(
              f"🗓️  {short_label}（残数: {rem_seats}名）", key=slot_key
          )
          if cb:
            selected_slots.append(slot_key)

    st.write("")
    st.markdown("### 📋 お客様情報の入力")

    name = st.text_input("お名前（必須）", placeholder="例: 山田 太郎")
    email = st.text_input("メールアドレス（必須）", placeholder="例: example@email.com")
    age = st.number_input("年齢（必須）", min_value=1, max_value=120, value=20)
    phone = st.text_input("電話番号（必須）", placeholder="例: 090-1234-5678")
    comment = st.text_area(
        "ご質問・ご要望（任意）", placeholder="気になる点などがあればご記入ください"
    )

    st.write("")
    submit_btn = st.form_submit_button("確認画面へ進む", use_container_width=True)

  if submit_btn:
    # バリデーションチェック
    email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    phone_pattern = r"^\d{2,4}-?\d{2,4}-?\d{3,4}$"

    if not selected_slots:
      st.warning("⚠️ 参加日時を少なくとも1つ選択してください。")
    elif not name.strip():
      st.warning("⚠️ お名前を入力してください。")
    elif not email.strip() or not re.match(email_pattern, email.strip()):
      st.warning("⚠️ 正しいメールアドレスの形式で入力してください。")
    elif not phone.strip() or not re.match(phone_pattern, phone.strip()):
      st.warning("⚠️ 正しい電話番号を入力してください（ハイフン可）。")
    else:
      # 最新の空き枠チェック（同時送信の重複防止）
      latest_counts = get_slot_counts()
      overbooked = False
      for s_key in selected_slots:
        if CAPACITY_LIMIT - latest_counts.get(s_key, 0) <= 0:
          overbooked = True
          st.error(
              f"申し訳ありません。選択された「{SLOTS[s_key]}」は直前に満席となりました。"
          )

      if not overbooked:
        st.session_state["form_data"] = {
            "selected_slots": selected_slots,
            "name": name.strip(),
            "email": email.strip(),
            "age": age,
            "phone": phone.strip(),
            "comment": comment.strip(),
        }
        st.session_state["page_step"] = 2
        st.rerun()


# ==========================================
# 🚀 ページ 2: 確認画面
# ==========================================
elif st.session_state["page_step"] == 2:

  data = st.session_state["form_data"]
  selected_slot_names = [SLOTS[k] for k in data["selected_slots"]]

  st.markdown("### 📋 ご予約内容の確認")
  st.info("以下の内容で間違いがなければ「予約を確定する」を押してください。")

  with st.container(border=True):
    st.markdown("#### ■ 選択された日時")
    for s_name in selected_slot_names:
      st.write(f"・ {shorten_date_str(s_name)}")

    st.markdown("---")
    st.markdown("#### ■ お客様情報")
    st.write(f"**お名前:** {data['name']} 様")
    st.write(f"**メールアドレス:** {data['email']}")
    st.write(f"**年齢:** {data['age']} 歳")
    st.write(f"**電話番号:** {data['phone']}")
    if data["comment"]:
      st.write(f"**ご質問・ご要望:** {data['comment']}")

  st.write("")
  col1, col2 = st.columns(2)

  with col1:
    if st.button("← 修正する", use_container_width=True):
      st.session_state["page_step"] = 1
      st.rerun()

  with col2:
    if st.button("予約を確定する", type="primary", use_container_width=True):
      try:
        ws = get_worksheet()

        # 確定直前に再度の定員オーバーチェック
        latest_counts = get_slot_counts()
        for s_key in data["selected_slots"]:
          if CAPACITY_LIMIT - latest_counts.get(s_key, 0) <= 0:
            st.error(
                f"申し訳ありません。選択された「{SLOTS[s_key]}」が直前で満席になりました。"
            )
            st.session_state["page_step"] = 1
            st.rerun()

        # スプレッドシートへ書き込み
        import datetime

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        joined_slots = "\n".join(selected_slot_names)

        new_row = [
            data["name"],
            data["email"],
            data["age"],
            data["phone"],
            data["comment"],
            joined_slots,
            now_str,
            "確定",
        ]

        ws.append_row(new_row)

        # 確認メール送信
        send_confirmation_email(
            data["email"],
            data["name"],
            data["age"],
            data["phone"],
            data["comment"],
            selected_slot_names,
        )

        st.session_state["page_step"] = 3
        st.cache_resource.clear()
        st.rerun()

      except Exception as e:
        st.error(f"⚠️ 予約処理中にエラーが発生しました: {e}")


# ==========================================
# 🚀 ページ 3: 完了画面
# ==========================================
elif st.session_state["page_step"] == 3:

  data = st.session_state.get("form_data", {})
  selected_slot_names = [SLOTS[k] for k in data.get("selected_slots", [])]

  st.success("🎉 ご予約が完了いたしました！")

  with st.container(border=True):
    st.markdown("### 📄 予約完了内容")
    for s_name in selected_slot_names:
      st.write(f"・ {shorten_date_str(s_name)}")

    st.write("")
    st.write(
        f"✉️ **{data.get('email')}** へ確認メールを送信いたしました。<br>"
        "メールが届かない場合は、迷惑メールフォルダをご確認いただくか、お問い合わせください。",
        unsafe_allow_html=True,
    )

  st.write("")
  if st.button("トップ画面に戻る", use_container_width=True):
    st.session_state["page_step"] = 1
    st.rerun()
