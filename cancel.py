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
if "matching_rows" not in st.session_state:
    st.session_state["matching_rows"] = []

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
            
            matching_rows = []
            # 2行目以降をチェック（1行目は見出し）
            for i, row in enumerate(all_records[1:], start=2):
                if len(row) >= 2 and row[0].strip() == cancel_name.strip() and row[1].strip() == cancel_email.strip():
                    current_status = row[7] if len(row) >= 8 else ""
                    if current_status == "確定":
                        dates_str = row[5] if len(row) >= 6 else "日時記載なし"
                        matching_rows.append({
                            "row_index": i,
                            "dates": dates_str
                        })
            
            st.session_state["matching_rows"] = matching_rows
            st.session_state["search_done"] = True
            st.session_state["search_name"] = cancel_name.strip()
            st.session_state["search_email"] = cancel_email.strip()
            
        except Exception as e:
            st.error(f"⚠️ 検索中にエラーが発生しました: {e}")

# 検索結果が存在する場合、対象日時の選択フォームを表示
if st.session_state.get("search_done"):
    matching_rows = st.session_state.get("matching_rows", [])
    
    if not matching_rows:
        st.error("⚠️ 該当する有効なご予約が見つかりませんでした。お名前・メールアドレスをご確認いただくか、既にキャンセル済みかご確認ください。")
    else:
        st.markdown("---")
        st.subheader("📋 キャンセルするご予約の選択")
        st.write(f"**{st.session_state['search_name']}** 様のご予約情報が見つかりました。キャンセルしたいご予約日時を選択してください。")
        
        # 選択肢の作成（行番号をKey、日時文字列をLabelにする）
        options_dict = {f"予約日時: {item['dates']}": item["row_index"] for item in matching_rows}
        
        selected_label = st.radio(
            "キャンセルするご予約を選択してください：",
            options=list(options_dict.keys())
        )
        
        if st.button("選んだご予約をキャンセルする", type="primary"):
            target_row_index = options_dict[selected_label]
            try:
                ws = get_worksheet()
                # H列（8列目）のステータスを「キャンセル済み」に変更
                ws.update_cell(target_row_index, 8, "キャンセル済み")
                
                # キャンセル完了メールの送信
                subject = "【キャンセル完了】イベント参加予約のキャンセルを承りました"
                body = f"""{st.session_state['search_name']} 様

イベント参加予約のキャンセル手続きが完了いたしました。

----------------------------------------
■ キャンセル対象日時：
{selected_label.replace('予約日時: ', '')}
----------------------------------------

またの機会がございましたら、ご参加を心よりお待ちしております。

----------------------------------------
【お問い合わせ先】
{CONTACT_EMAIL}
----------------------------------------
"""
                send_email(st.session_state['search_email'], subject, body)
                
                st.success("✅ ご予約のキャンセル処理が完了いたしました。")
                st.info("✉️ キャンセル完了の確認メールを送信しました。")
                
                # セッション初期化
                st.session_state["search_done"] = False
                st.session_state["matching_rows"] = []
                st.cache_resource.clear()
                
            except Exception as e:
                st.error(f"⚠️ キャンセル処理中にエラーが発生しました: {e}")
