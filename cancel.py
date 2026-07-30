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
CONTACT_EMAIL = "hanaizu64@gmail.com" 

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
st.write("ご予約時に入力した「お名前」と「メールアドレス」を入力して予約内容を検索してください。")

# セッション状態の初期化
if "search_done" not in st.session_state:
    st.session_state["search_done"] = False
if "found_rows" not in st.session_state:
    st.session_state["found_rows"] = []

with st.form("search_form"):
    cancel_name = st.text_input("お名前（フルネーム）*", placeholder="例: 山田 太郎")
    cancel_email = st.text_input("メールアドレス*", placeholder="例: example@email.com")
    
    search_submit = st.form_submit_button("予約内容を検索する")

if search_submit:
    if not cancel_name or not cancel_email:
        st.warning("⚠️ お名前とメールアドレスの両方を入力してください。")
        st.session_state["search_done"] = False
    else:
        try:
            ws = get_worksheet()
            all_records = ws.get_all_values()
            
            found_rows = []
            # 2行目以降をチェック（1行目は見出し）
            for i, row in enumerate(all_records[1:], start=2):
                if len(row) >= 2 and row[0].strip() == cancel_name.strip() and row[1].strip() == cancel_email.strip():
                    current_status = row[7] if len(row) >= 8 else ""
                    if current_status == "確定":
                        dates_str = row[5] if len(row) >= 6 else ""
                        # 「、」で分割して個別の日時リストにする
                        dates_list = [d.strip() for d in dates_str.split("、") if d.strip()]
                        found_rows.append({
                            "row_index": i,
                            "dates_list": dates_list
                        })
            
            st.session_state["found_rows"] = found_rows
            st.session_state["search_done"] = True
            st.session_state["search_name"] = cancel_name.strip()
            st.session_state["search_email"] = cancel_email.strip()
            
        except Exception as e:
            st.error(f"⚠️ 検索中にエラーが発生しました: {e}")

# 検索結果が存在する場合、キャンセルしたい日時の選択フォームを表示
if st.session_state.get("search_done"):
    found_rows = st.session_state.get("found_rows", [])
    
    if not found_rows:
        st.error("⚠️ 該当する有効なご予約が見つかりませんでした。お名前・メールアドレスをご確認いただくか、既にキャンセル済みかご確認ください。")
    else:
        st.markdown("---")
        st.subheader("📋 キャンセルする日時の選択")
        st.write(f"**{st.session_state['search_name']}** 様の有効なご予約が見つかりました。")
        st.write("キャンセルしたい日時を選択（複数選択可）して、「選んだ日時をキャンセルする」を押してください。")
        
        # すべての予約日時をまとめたリストを作成
        all_dates_options = []
        for item in found_rows:
            all_dates_options.extend(item["dates_list"])
        
        # 重複を除去
        unique_dates_options = list(dict.fromkeys(all_dates_options))
        
        # 複数選択可能なマルチセレクトを表示
        selected_cancel_dates = st.multiselect(
            "キャンセルしたい日時を選んでください：",
            options=unique_dates_options
        )
        
        if st.button("選んだ日時をキャンセルする", type="primary"):
            if not selected_cancel_dates:
                st.warning("⚠️ キャンセルしたい日時を1つ以上選択してください。")
            else:
                try:
                    ws = get_worksheet()
                    
                    # 各行について処理
                    for item in found_rows:
                        row_idx = item["row_index"]
                        original_dates = item["dates_list"]
                        
                        # 残す日時を計算（キャンセル対象に含まれない日時）
                        remaining_dates = [d for d in original_dates if d not in selected_cancel_dates]
                        
                        if not remaining_dates:
                            # すべてキャンセルされた場合はステータスを「キャンセル済み」に変更し、F列の日時はそのまま保持
                            ws.update_cell(row_idx, 8, "キャンセル済み")
                        else:
                            # 一部キャンセルされた場合は、F列に残った日時だけを「、」区切りで上書き更新
                            new_dates_str = "、".join(remaining_dates)
                            ws.update_cell(row_idx, 6, new_dates_str)
                    
                    # キャンセル完了メールの送信
                    cancel_dates_formatted = "、\n".join(selected_cancel_dates)
                    subject = "【キャンセル完了】イベント参加予約のキャンセルを承りました"
                    body = f"""{st.session_state['search_name']} 様

イベント参加予約のキャンセル手続きが完了いたしました。

----------------------------------------
■ キャンセルした日時：
{cancel_dates_formatted}
----------------------------------------

またの機会がございましたら、ご参加を心よりお待ちしております。

----------------------------------------
【お問い合わせ先】
{CONTACT_EMAIL}
----------------------------------------
"""
                    send_email(st.session_state['search_email'], subject, body)
                    
                    st.success("✅ 選択された日時のキャンセル処理が完了いたしました！")
                    st.info("✉️ キャンセル完了の確認メールを送信しました。")
                    
                    # セッション初期化
                    st.session_state["search_done"] = False
                    st.session_state["found_rows"] = []
                    st.cache_resource.clear()
                    
                except Exception as e:
                    st.error(f"⚠️ キャンセル処理中にエラーが発生しました: {e}")
