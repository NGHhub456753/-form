import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.service_account import Credentials
import gspread
import pandas as pd
import streamlit as st

# --- ページ設定 ---
st.set_page_config(page_title="ご予約キャンセル受付", page_icon="❌")

SPREADSHEET_NAME = "イベント予約一覧"  # Googleスプレッドシートのファイル名

# ★ 明日新しいアドレスが決まったらここを変更してください
CONTACT_EMAIL = "新しいお問い合わせ用メアド@gmail.com"  # 問い合わせ先アドレス
ADMIN_EMAIL = "hanaizu64@gmail.com"  # 管理者（自分）のアドレス


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


# --- メール送信関数（予約者＋管理者＋お問い合わせ先の全宛気に送信） ---
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
if "cancel_step" not in st.session_state:
  st.session_state["cancel_step"] = 1

# スマホ調整CSS付きタイトル
st.markdown(
    """
    <style>
    .custom-title {
        font-size: 1.7rem !important;
        font-weight: bold;
        margin-bottom: 0.5rem;
        word-break: keep-all;
        white-space: nowrap;
    }
    </style>
    <h1 class="custom-title">❌ ご予約キャンセル</h1>
""",
    unsafe_allow_html=True,
)

# ==========================================
# ステップ 1: 予約照会（検索）画面
# ==========================================
if st.session_state["cancel_step"] == 1:
  st.write(
      "ご予約時にご登録いただいた「お名前」と「メールアドレス」を入力して検索してください。"
  )

  with st.form("search_form"):
    search_name = st.text_input(
        "お名前（フルネーム）*", placeholder="例: 山田 太郎"
    )
    search_email = st.text_input(
        "メールアドレス*", placeholder="例: example@email.com"
    )
    search_button = st.form_submit_button("予約を検索する")

  if search_button:
    if not search_name or not search_email:
      st.warning("⚠️ お名前とメールアドレスの両方を入力してください。")
    else:
      try:
        ws = get_worksheet()
        all_records = ws.get_all_values()

        found_rows = []
        for i, row in enumerate(all_records[1:], start=2):
          if len(row) >= 2:
            name_val = row[0].strip()
            email_val = row[1].strip()
            status_val = row[7].strip() if len(row) >= 8 else ""

            if (
                name_val == search_name.strip()
                and email_val == search_email.strip()
                and status_val != "キャンセル済"
            ):
              dates_str = row[5] if len(row) >= 6 else ""
              dates_list = [
                  d.strip() for d in dates_str.split("、") if d.strip()
              ]
              found_rows.append({"row_index": i, "dates_list": dates_list})

        if not found_rows:
          st.error(
              "❌"
              " 該当するご予約が見つかりませんでした。入力内容をご確認いただくか、すでにキャンセル処理が完了している可能性があります。"
          )
        else:
          st.session_state["found_rows"] = found_rows
          st.session_state["search_name"] = search_name.strip()
          st.session_state["search_email"] = search_email.strip()
          st.session_state["cancel_step"] = 2
          st.rerun()

      except Exception as e:
        st.error(f"⚠️ 検索中にエラーが発生しました: {e}")

# ==========================================
# ステップ 2: 日時選択・キャンセル確定画面
# ==========================================
elif st.session_state["cancel_step"] == 2:
  found_rows = st.session_state.get("found_rows", [])

  st.subheader("📋 キャンセルする日時の選択")
  st.write(f"**{st.session_state['search_name']}** 様のご予約が見つかりました。")
  st.write(
      "キャンセルしたい日時を選択（複数選択可）して、「選んだ日時をキャンセルする」を押してください。"
  )

  all_dates = []
  for item in found_rows:
    all_dates.extend(item["dates_list"])
  unique_dates = list(dict.fromkeys(all_dates))

  selected_cancel_dates = st.multiselect(
      "キャンセルしたい日時を選んでください：", options=unique_dates
  )

  col1, col2 = st.columns([1, 1])

  with col1:
    if st.button("選んだ日時をキャンセルする", type="primary"):
      if not selected_cancel_dates:
        st.warning("⚠️ キャンセルしたい日時を1つ以上選択してください。")
      else:
        try:
          ws = get_worksheet()

          for item in found_rows:
            row_idx = item["row_index"]
            original_dates = item["dates_list"]

            remaining_dates = [
                d for d in original_dates if d not in selected_cancel_dates
            ]

            if not remaining_dates:
              # 全キャンセルの場合は希望日時を空欄にし、ステータスをキャンセル済へ
              ws.update_cell(row_idx, 6, "")
              ws.update_cell(row_idx, 8, "キャンセル済")
            else:
              # 一部キャンセルの場合は残った日時で更新
              new_dates_str = "、".join(remaining_dates)
              ws.update_cell(row_idx, 6, new_dates_str)

          # キャンセル完了メール送信（予約者＆管理者＆お問い合わせ先）
          cancel_dates_formatted = "、\n".join(selected_cancel_dates)
          subject = (
              "【キャンセル完了】イベント予約のキャンセルを受け付けました"
          )
          body = f"""{st.session_state['search_name']} 様

イベント予約のキャンセル手続きが完了いたしました。

----------------------------------------
■ キャンセルした日時：
{cancel_dates_formatted}
----------------------------------------

またの機会がございましたら、ご参加を心よりお待ちしております。

【お問い合わせ】
{CONTACT_EMAIL}
"""
          send_email(st.session_state["search_email"], subject, body)

          st.session_state["cancelled_dates_str"] = "、".join(
              selected_cancel_dates
          )
          st.session_state["cancel_step"] = 3
          st.rerun()

        except Exception as e:
          st.error(f"⚠️ キャンセル処理中にエラーが発生しました: {e}")

  with col2:
    if st.button("← 最初からやり直す"):
      st.session_state["cancel_step"] = 1
      st.session_state["found_rows"] = []
      st.rerun()

# ==========================================
# ステップ 3: キャンセル完了画面
# ==========================================
elif st.session_state["cancel_step"] == 3:
  st.success(
      f"✅ {st.session_state['search_name']}"
      " 様のご予約キャンセル手続きが完了しました。"
  )
  st.info("ご登録のメールアドレス宛に、キャンセル確認メールをお送りしました。")

  st.markdown("---")
  st.write(
      f"**キャンセル完了日時:** {st.session_state['cancelled_dates_str']}"
  )
  st.markdown("---")

  if st.button("← 最初に戻る"):
    st.session_state["cancel_step"] = 1
    st.session_state["found_rows"] = []
    st.rerun()
