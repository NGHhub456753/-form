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

# ★ 担当者様のお問い合わせ先メールアドレス（新しいアドレスに変更してください）
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

# ★ タイトル（スマホでも1行に収まる調整CSS付き）
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
                data = ws.get_all_records()
                df = pd.DataFrame(data)

                if df.empty:
                    st.error("❌ 現在、予約データが存在しません。")
                else:
                    # 名前・メールの一致かつ、キャンセルされていないデータ（Status!=キャンセル）を検索
                    # 列名が合致しているか確認（名前, メールアドレス, ステータス）
                    filtered_df = df[
                        (df["名前"].astype(str).str.strip() == search_name.strip()) & 
                        (df["メールアドレス"].astype(str).str.strip() == search_email.strip()) &
                        (df["ステータス"].astype(str) != "キャンセル")
                    ]

                    if filtered_df.empty:
                        st.error("❌ 該当するご予約が見つかりませんでした。入力内容（お名前・メールアドレス）をご確認いただくか、すでにキャンセル処理が完了している可能性があります。")
                    else:
                        st.session_state["found_reservation"] = filtered_df
                        st.session_state["search_name"] = search_name
                        st.session_state["search_email"] = search_email

            except Exception as e:
                st.error(f"⚠️ 照会中にエラーが発生しました: {e}")

    # 検索結果が存在する場合にキャンセルの選択を表示
    if "found_reservation" in st.session_state:
        st.markdown("---")
        st.success("🎉 ご予約情報が見つかりました。キャンセルする日程を選択してください。")
        
        found_df = st.session_state["found_reservation"]
        
        for idx, row in found_df.iterrows():
            st.markdown(f"**お名前:** {row['名前']} 様")
            st.markdown(f"**人数:** {row['人数']}")
            st.markdown(f"**ご予約日時:** {row['希望日時']}")
            
            # スプレッドシートの行番号を計算 (ヘッダー1行 + 1-indexed)
            row_number = idx + 2
            
            cancel_reason = st.text_input("キャンセル理由（任意）", key=f"reason_{row_number}")
            
            if st.button("この予約をキャンセルする", key=f"btn_{row_number}"):
                try:
                    ws = get_worksheet()
                    # H列（ステータス）を「キャンセル」に更新
                    ws.update_cell(row_number, 8, "キャンセル")
                    
                    # キャンセル通知メール送信
                    subject = "【キャンセル完了】イベント予約のキャンセルを受け付けました"
                    body = f"""{row['名前']} 様

いつもご利用いただきありがとうございます。
以下のイベントご予約のキャンセル手続きが完了いたしました。

----------------------------------------
■ キャンセル完了日時：
{row['希望日時']}

■ 人数：{row['人数']}
----------------------------------------

またのご機会がございましたら、ご参加を心よりお待ちしております。

【お問い合わせ】
ご不明な点がございましたら、以下のアドレスまでご連絡ください。
お問い合わせ先：{CONTACT_EMAIL}
"""
                    send_email(row['メールアドレス'], subject, body)
                    
                    st.session_state["cancelled_name"] = row['名前']
                    st.session_state["cancelled_dates"] = row['希望日時']
                    st.session_state["cancel_step"] = 2
                    
                    # 検索結果セッションの削除
                    del st.session_state["found_reservation"]
                    st.cache_resource.clear()
                    st.rerun()

                except Exception as e:
                    st.error(f"⚠️ キャンセル処理中にエラーが発生しました: {e}")

# ==========================================
# ステップ 2: キャンセル完了画面（フォーム非表示）
# ==========================================
elif st.session_state["cancel_step"] == 2:
    st.success(f"✅ {st.session_state['cancelled_name']} 様のご予約キャンセル手続きが完了しました。")
    st.info(f"ご登録のメールアドレス宛に、キャンセル確認メールをお送りしました。")
    
    st.markdown("---")
    st.write(f"**キャンセル完了内容:** {st.session_state['cancelled_dates']}")
    st.markdown("---")
    
    if st.button("← トップページに戻る"):
        st.session_state["cancel_step"] = 1
        st.rerun()
