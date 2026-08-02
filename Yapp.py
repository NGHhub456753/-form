import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.service_account import Credentials
import gspread
import streamlit as st

# ==========================================
# ⚙️ 基本設定 & 定数
# ==========================================
st.set_page_config(
    page_title="折り紙体験ワークショップ 予約キャンセル", page_icon="❌"
)

SPREADSHEET_NAME = "イベント予約一覧"
CONTACT_EMAIL = "aonisai0111@gmail.com"
ADMIN_EMAIL = "aonisai0111@gmail.com"


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


def send_cancel_email(to_email, name, cancelled_dates):
  try:
    sender_email = st.secrets["smtp"]["email"]
    sender_password = st.secrets["smtp"]["password"]

    msg = MIMEMultipart("alternative")
    msg["From"] = f"イベント事務局 <{sender_email}>"
    msg["To"] = to_email
    msg["Reply-To"] = CONTACT_EMAIL
    msg["Subject"] = "【キャンセル受付】折り紙体験ワークショップの予約キャンセル"

    dates_html = "<br>".join([f"・ {d}" for d in cancelled_dates])

    body_html = f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; line-height: 1.6; color: #333333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <p>{name} 様</p>
    <p>「折り紙体験ワークショップ」の以下のご予約キャンセルを受け付けいたしました。</p>
    
    <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 15px; margin: 20px 0;">
        <h3 style="margin-top:0; color: #991b1b; border-bottom: 2px solid #f87171; padding-bottom: 5px;">■ キャンセルされた日時</h3>
        <p style="font-size: 15px; line-height: 1.8; color: #7f1d1d;">
            {dates_html}
        </p>
    </div>

    <p>またのご参加を心よりお待ちしております。</p>
    
    <hr style="border: none; border-top: 1px dashed #cbd5e1; margin: 25px 0;">
    <p style="font-size: 13px; color: #64748b;">
        ご不明な点がございましたら以下までご連絡ください。<br>
        お問い合わせ先：<a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>
    </p>
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
# 🚀 アプリメイン処理
# ==========================================
st.markdown(
    """<style>
.cancel-header {
    background-color: #FEF2F2;
    padding: 18px 20px;
    border-radius: 12px;
    border-left: 6px solid #EF4444;
    margin-bottom: 20px;
}
.cancel-title {
    font-size: 1.4rem !important;
    font-weight: 800;
    color: #991B1B;
    margin: 0;
}
.checkbox-card {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 10px;
}
</style>

<div class="cancel-header">
    <div class="cancel-title">❌ ご予約キャンセル手続き</div>
</div>
""",
    unsafe_allow_html=True,
)

if "user_found" not in st.session_state:
  st.session_state["user_found"] = False

# ------------------------------------------
# ステップ 1: メールアドレス検索
# ------------------------------------------
with st.form("search_form"):
  st.subheader("🔍 ご予約の確認")
  search_email = st.text_input(
      "ご予約時のメールアドレスを入力してください",
      placeholder="例: example@email.com",
  )
  search_btn = st.form_submit_button("予約を検索する")

if search_btn:
  if not search_email:
    st.warning("⚠️ メールアドレスを入力してください。")
  else:
    try:
      ws = get_worksheet()
      all_records = ws.get_all_values()

      # ヘッダーを除いたデータ行を検索（列構造: 0:名前, 1:メール, 2:電話, 3:人数, 4:認知, 5:日時, 6:備考, 7:ステータス）
      found_rows = []
      for idx, row in enumerate(all_records[1:], start=2):
        if len(row) >= 8:
          r_email = row[1].strip()
          r_status = row[7].strip()
          if r_email.lower() == search_email.strip().lower() and r_status != "キャンセル":
            found_rows.append((idx, row))

      if not found_rows:
        st.error(
            "❌ 該当するご予約が見つかりませんでした。メールアドレスをご確認ください。"
        )
        st.session_state["user_found"] = False
      else:
        # 最新の予約を採用
        target_row_idx, target_row = found_rows[-1]
        raw_dates = target_row[5].split("\n")
        dates_list = [d.strip() for d in raw_dates if d.strip()]

        st.session_state["user_found"] = True
        st.session_state["target_row_idx"] = target_row_idx
        st.session_state["target_name"] = target_row[0]
        st.session_state["target_email"] = target_row[1]
        st.session_state["target_dates"] = dates_list
        st.session_state["full_row"] = target_row

    except Exception as e:
      st.error(f"⚠️ データ取得エラーが発生しました: {e}")

# ------------------------------------------
# ステップ 2: チェックボックス選択 & キャンセル実行
# ------------------------------------------
if st.session_state.get("user_found", False):
  st.markdown("---")
  st.subheader("📋 キャンセルする日時の選択")
  st.write(
      f"**{st.session_state['target_name']} 様** のご予約が見つかりました。"
  )
  st.info("キャンセルしたい日時にチェックを入れて「選択した日時をキャンセルする」を押してください。")

  # チェックボックスで選択肢を作成
  cancelled_selected = []
  
  with st.form("cancel_confirm_form"):
    for idx, date_str in enumerate(st.session_state["target_dates"]):
      cb = st.checkbox(f"🗓️ {date_str}", key=f"cb_{idx}")
      if cb:
        cancelled_selected.append(date_str)

    st.write("")
    cancel_submit = st.form_submit_button("選択した日時をキャンセルする")

  if cancel_submit:
    if not cancelled_selected:
      st.warning("⚠️ キャンセルする日時を少なくとも1つ選択してください。")
    else:
      try:
        ws = get_worksheet()
        row_idx = st.session_state["target_row_idx"]

        remaining_dates = [
            d
            for d in st.session_state["target_dates"]
            if d not in cancelled_selected
        ]

        if not remaining_dates:
          # 全てキャンセルされた場合：ステータスを「キャンセル」に変更
          ws.update_cell(row_idx, 6, "")  # 日時クリア
          ws.update_cell(row_idx, 8, "キャンセル")
        else:
          # 一部キャンセルされた場合：日時リストを更新
          updated_dates_str = "\n".join(remaining_dates)
          ws.update_cell(row_idx, 6, updated_dates_str)

        # キャンセルメール送信
        send_cancel_email(
            st.session_state["target_email"],
            st.session_state["target_name"],
            cancelled_selected,
        )

        st.success("✅ ご予約のキャンセル手続きが完了いたしました。")
        st.session_state["user_found"] = False
        st.cache_resource.clear()

      except Exception as e:
        st.error(f"⚠️ キャンセル処理中にエラーが発生しました: {e}")
