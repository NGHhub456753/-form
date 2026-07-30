import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- ページ設定 ---
st.set_page_config(page_title="イベント予約システム", page_icon="📝")

SPREADSHEET_NAME = "イベント予約一覧"  # Googleスプレッドシートのファイル名

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

# --- メイン画面：日時選択 ---
st.title("📝 イベント参加予約フォーム")
st.write("ご希望の日時を選択し、必要事項を入力して「予約を確定する」を押してください。")

dates = [
    "8月24日 14:00〜",
    "8月24日 18:00〜",
    "8月25日 14:00〜",
    "8月25日 18:00〜"
]
selected_date = st.selectbox("参加希望日時を選んでください", dates)

st.markdown("---")

# --- 予約入力フォーム ---
with st.form("booking_form"):
    st.subheader("参加者情報の入力")
    name = st.text_input("お名前（フルネーム）", placeholder="例: 山田 太郎")
    email = st.text_input("メールアドレス", placeholder="例: example@email.com")
    
    # ★ 参加人数の選択項目を追加
    num_people = st.selectbox(
        "参加人数",
        options=["1名", "2名", "3名", "4名", "5名以上（備考欄にご記入ください）"]
    )
    
    note = st.text_area("ご質問・ご要望（任意）", placeholder="配慮事項や、複数人でお越しの際のご連絡などがあればご記入ください")
    
    submit_button = st.form_submit_button("予約を確定する")

# --- 送信時の処理 ---
if submit_button:
    if not name or not email:
        st.warning("⚠️ お名前とメールアドレスは必須項目です。")
    elif "@" not in email or "." not in email:
        st.warning("⚠️ 有効なメールアドレスの形式で入力してください。")
    else:
        try:
            ws = get_worksheet()
            # スプレッドシートに [名前, メールアドレス, 参加人数, 希望日時, 備考] の順で保存
            ws.append_row([name, email, num_people, selected_date, note])
            
            st.balloons()
            st.success(f"🎉 {name} 様（{num_people}）、ご予約が完了しました！")
            st.write(f"**確定日時:** {selected_date}")
            st.cache_resource.clear()  # キャッシュをクリア
        except Exception as e:
            st.error(f"⚠️ 保存エラーが発生しました: {e}")
