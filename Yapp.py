import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- ページ設定 ---
st.set_page_config(page_title="イベント予約システム", page_icon="📝")

CAPACITY = 10
SPREADSHEET_NAME = "イベント予約一覧"  # Step 1で作ったスプレッドシートの正確な名前

# --- Google Sheets 接続関数 ---
@st.cache_resource
def get_gspread_client():
    # Streamlit Secrets から認証情報を読み込み
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    return gspread.authorize(credentials)

def get_worksheet():
    client = get_gspread_client()
    sheet = client.open(SPREADSHEET_NAME)
    return sheet.sheet1

# 予約データの読み込み関数
def load_data():
    try:
        ws = get_worksheet()
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        return pd.DataFrame()

# 既存の予約数をカウントする関数
def get_booking_count(selected_date):
    df = load_data()
    if not df.empty and "希望日時" in df.columns:
        return len(df[df["希望日時"] == selected_date])
    return 0

# --- メイン画面：日時選択 ---
st.title("📝 イベント参加予約フォーム")
st.write("ご希望の日時を選択し、必要事項を入力して「予約する」を押してください。")

dates = [
    "8月24日 14:00〜",
    "8月24日 18:00〜",
    "8月25日 14:00〜",
    "8月25日 18:00〜"
]
selected_date = st.selectbox("参加希望日時を選んでください", dates)

# 残り枠数の計算
current_count = get_booking_count(selected_date)
remaining_seats = CAPACITY - current_count

if remaining_seats > 0:
    st.info(f"💡 【{selected_date}】の残り枠数: あと **{remaining_seats}** 名")
else:
    st.error(f"⚠️ 【{selected_date}】は満席です。別の日時を選択してください。")

st.markdown("---")

# --- 予約入力フォーム ---
with st.form("booking_form"):
    st.subheader("参加者情報の入力")
    name = st.text_input("お名前（フルネーム）", placeholder="例: 山田 太郎")
    email = st.text_input("メールアドレス", placeholder="例: example@email.com")
    note = st.text_area("ご質問・ご要望（任意）", placeholder="配慮事項などがあればご記入ください")
    
    submit_button = st.form_submit_button("予約を確定する", disabled=(remaining_seats <= 0))

# --- 送信時の処理 ---
if submit_button:
    if not name or not email:
        st.warning("⚠️ お名前とメールアドレスは必須項目です。")
    elif "@" not in email or "." not in email:
        st.warning("⚠️ 有効なメールアドレスの形式で入力してください。")
    else:
        try:
            ws = get_worksheet()
            # スプレッドシートの最終行に直接追加
            ws.append_row([name, email, selected_date, note])
            
            st.balloons()
            st.success(f"🎉 {name} 様、ご予約が完了しました！")
            st.write(f"**確定日時:** {selected_date}")
        except Exception as e:
            st.error("⚠️ 予約データの保存中にエラーが発生しました。設定を確認してください。")
