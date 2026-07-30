import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- ページ設定 ---
st.set_page_config(page_title="ご予約キャンセル受付", page_icon="❌")

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

# セッション状態の初期化
if "cancel_step" not in st.session_state:
    st.session_state["cancel_step"] = 1  # 1: 検索/照会画面, 2: 完了画面

# スマホ調整CSS付きタイトル
st.markdown("""
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
""", unsafe_allow_html=True)

# ==========================================
# ステップ 1: 予約照会・キャンセル選択画面
# ==========================================
if st.session_state["cancel_step"] == 1:
    st.write("ご予約時にご登録いただいた「お名前」と「メールアドレス」を入力して検索してください。")

    with st.form("search_form"):
        search_name = st.text_input("お名前（フルネーム）*", placeholder="例: 山田 太郎")
        search_email = st.text_input("メールアドレス*", placeholder="例: example@email.com")
        search_button = st.form_submit_button("予約を照会する")

    if search_button:
        if not search_name or not search_email:
            st.warning("⚠️ お名前とメールアドレスの両方を入力してください。")
        else:
            try:
                ws = get_worksheet()
                all_records = ws.get_all_values()
                
                found_rows = []
                # 2行目以降（実データ）を順番にチェック
                for i, row in enumerate(all_records[1:], start=2):
                    # 列数が足りているかチェック
                    if len(row) >= 2:
                        name_val = row[0].strip()   # 1列目: お名前
                        email_val = row[1].strip()  # 2列目: メールアドレス
                        status_val = row[7].strip() if len(row) >= 8 else "" # 8列目: ステータス
                        
                        if name_val == search_name.strip() and email_val == search_email.strip() and status_val != "キャンセル":
                            found_rows.append({
                                "row_index": i,
                                "name": name_val,
                                "email": email_val,
                                "num_people": row[3] if len(row) >= 4 else "",
                                "dates": row[5] if len(row) >= 6 else ""
                            })

                if not found_rows:
                    st.error("❌ 該当するご予約が見つかりませんでした。入力内容をご確認いただくか、すでにキャンセル処理が完了している可能性があります。")
                else:
                    st.session_state["found_rows"] = found_rows
                    st.session_state["search_name"] = search_name
                    st.session_state["search_email"] = search_email

            except Exception as e:
                st.error(f"⚠️ 照会中にエラーが発生しました: {e}")

    # 検索結果が存在する場合に表示
    if "found_rows" in st.session_state and st.session_state["found_rows"]:
        st.markdown("---")
        st.success("🎉 ご予約情報が見つかりました。キャンセルするご予約を確認してください。")
        
        for item in st.session_state["found_rows"]:
            row_idx = item["row_index"]
            st.markdown(f"**お名前:** {item['name']} 様")
            st.markdown(f"**人数:** {item['num_people']}")
            st.markdown(f"**ご予約日時:** {item['dates']}")
            
            if st.button("この予約をキャンセルする", key=f"btn_{row_idx}", type="primary"):
                try:
                    ws = get_worksheet()
                    # H列（8列目）を「キャンセル」に更新
                    ws.update_cell(row_idx, 8, "キャンセル")
                    
                    # キャンセル通知メール送信
                    subject = "【キャンセル完了】イベント予約のキャンセルを受け付けました"
                    body = f"""{item['name']} 様

いつもご利用いただきありがとうございます。
以下のイベントご予約のキャンセル手続きが完了いたしました。

----------------------------------------
■ キャンセル完了日時：
{item['dates']}

■ 人数：{item['num_people']}
----------------------------------------

またのご機会がございましたら、ご参加を心よりお待ちしております。

【お問い合わせ】
ご不明な点がございましたら、以下のアドレスまでご連絡ください。
お問い合わせ先：{CONTACT_EMAIL}
"""
                    send_email(item['email'], subject, body)
                    
                    st.session_state["cancelled_name"] = item['name']
                    st.session_state["cancelled_dates"] = item['dates']
                    st.session_state["cancel_step"] = 2
                    
                    if "found_rows" in st.session_state:
                        del st.session_state["found_rows"]
                    st.cache_resource.clear()
                    st.rerun()

                except Exception as e:
                    st.error(f"⚠️ キャンセル処理中にエラーが発生しました: {e}")

# ==========================================
# ステップ 2: キャンセル完了画面（フォーム非表示）
# ==========================================
elif st.session_state["cancel_step"] == 2:
    st.success(f"✅ {st.session_state['cancelled_name']} 様のご予約キャンセル手続きが完了しました。")
    st.info("ご登録のメールアドレス宛に、キャンセル確認メールをお送りしました。")
    
    st.markdown("---")
    st.write(f"**キャンセル完了日時:** {st.session_state['cancelled_dates']}")
    st.markdown("---")
    
    if st.button("← 最初に戻る"):
        st.session_state["cancel_step"] = 1
        st.rerun()
