import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- ページ設定 ---
st.set_page_config(page_title="イベント予約キャンセル受付", page_icon="❌")

SPREADSHEET_NAME = "イベント予約一覧"  # Googleスプレッドシートのファイル名

# ★ 担当者様のお問い合わせ先メールアドレス
CONTACT_EMAIL = "担当者@example.com" 

# --- Google Sheets 接続関数 ---
@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    service_account_info = dict(st.secrets["gcp_service_account"])
    service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")
    
    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=scopes
    )
    return gspread.authorize(credentials)

def get_worksheet():
    client = get_gspread_client()
    sheet = client.open(SPREADSHEET_NAME)
    return sheet.sheet1

# --- メール送信関数 ---
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

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.warning(f"⚠️ メール送信に失敗しました: {e}")
        return False

# --- メイン画面：キャンセルフォーム ---
st.title("❌ ご予約キャンセル受付フォーム")
st.write("ご予約時に入力した「お名前」と「メールアドレス」を入力して「キャンセルを確定する」を押してください。")

with st.form("cancel_form"):
    cancel_name = st.text_input("お名前（フルネーム）*", placeholder="例: 山田 太郎")
    cancel_email = st.text_input("メールアドレス*", placeholder="例: example@email.com")
    
    cancel_submit = st.form_submit_button("キャンセルを確定する")

if cancel_submit:
    if not cancel_name or not cancel_email:
        st.warning("⚠️ お名前とメールアドレスの両方を入力してください。")
    else:
        try:
            ws = get_worksheet()
            all_records = ws.get_all_values()
            
            found = False
            # 2行目以降をチェック（1行目は見出し）
            for i, row in enumerate(all_records[1:], start=2):
                if len(row) >= 2 and row[0].strip() == cancel_name.strip() and row[1].strip() == cancel_email.strip():
                    current_status = row[7] if len(row) >= 8 else ""
                    if current_status == "キャンセル済み":
                        st.info("ℹ️ このご予約はすでにキャンセル処理が完了しています。")
                        found = True
                        break
                    
                    # H列（8列目）のステータスを「キャンセル済み」に変更
                    ws.update_cell(i, 8, "キャンセル済み")
                    found = True
                    
                    # キャンセル完了メールをユーザーへ送信
                    subject = "【キャンセル完了】イベント参加予約のキャンセルを承りました"
                    body = f"""{cancel_name} 様

イベント参加予約のキャンセル手続きが完了いたしました。

またのご機会がございましたら、ご参加を心よりお待ちしております。

----------------------------------------
【お問い合わせ先】
{CONTACT_EMAIL}
----------------------------------------
"""
                    send_email(cancel_email, subject, body)
                    
                    st.success(f"✅ {cancel_name} 様のご予約のキャンセル処理が完了いたしました。")
                    st.info("✉️ キャンセル完了の確認メールを送信しました。")
                    st.cache_resource.clear()
                    break
            
            if not found:
                st.error("⚠️ 該当するご予約が見つかりませんでした。お名前とメールアドレスをご確認ください。")
                
        except Exception as e:
            st.error(f"⚠️ キャンセル処理中にエラーが発生しました: {e}")

