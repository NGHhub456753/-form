import datetime
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st

# ==========================================
# ページ設定
# ==========================================
st.set_page_config(
    page_title="ワークショップ参加申込",
    page_icon="🎨",
    layout="centered",
)

# Custom CSS for polished styling
st.markdown(
    """
    <style>
    /* 全体フォント・背景調整 */
    .stApp {
        font-family: 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif;
    }
    
    /* カードデザイン */
    .venue-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 5px solid #0284c7;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 12px;
    }
    .venue-title {
        font-size: 1.1rem;
        font-weight: bold;
        color: #0f172a;
        margin-bottom: 6px;
    }
    .venue-content {
        font-size: 0.9rem;
        color: #475569;
        line-height: 1.6;
    }
    
    /* フォーム区切り線 */
    hr {
        border-top: 1px solid #e2e8f0;
        margin: 2rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# Googleシート連携関数
# ==========================================
def save_to_google_sheet(data_row):
    """Googleスプレッドシートにデータを保存する関数"""
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        
        # Secrets からサービスアカウント情報を取得
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # スプレッドシートを開く
        sheet_url = st.secrets["spreadsheet"]["url"]
        sheet = client.open_by_url(sheet_url).sheet1
        
        # 行の追加
        sheet.append_row(data_row)
        return True
    except Exception as e:
        st.error(f"スプレッドシートへの保存中にエラーが発生しました: {e}")
        return False

# ==========================================
# メイン画面表示
# ==========================================
st.title("🎨 ワークショップ参加申込フォーム")
st.write("ご希望の日時を選択し、お客様情報を入力のうえ「送信する」ボタンを押してください。")

st.markdown("<hr>", unsafe_allow_html=True)

# ------------------------------------------
# ステップ 1: 希望日時の選択
# ------------------------------------------
st.subheader("1. 参加ご希望の日時を選択してください（複数選択可）")

# 会場 1: スターバックス インターパークスタジアム店
st.markdown(
    """
    <div class="venue-card">
        <div class="venue-title">📍 スターバックス インターパークスタジアム店</div>
        <div class="venue-content">
            内容：<br>
            ・14:00〜 折り紙でお花づくり<br>
            ・18:00〜 折り紙でランタン制作
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

d1 = st.checkbox("8月24日（月）14:00〜")
d2 = st.checkbox("8月24日（月）18:00〜")

st.markdown("<br>", unsafe_allow_html=True)

# 会場 2: スターバックス 宇都宮川田店
st.markdown(
    """
    <div class="venue-card">
        <div class="venue-title">📍 スターバックス 宇都宮川田店</div>
        <div class="venue-content">
            内容：<br>
            ・折り紙でお花づくり
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

d3 = st.checkbox("8月25日（火）10:00〜（折り紙でお花づくり）")

st.markdown("<hr>", unsafe_allow_html=True)

# ------------------------------------------
# ステップ 2: お客様情報の入力
# ------------------------------------------
st.subheader("2. お客様情報の入力")

with st.form(key="reservation_form"):
    name = st.text_input("お名前（必須）", placeholder="例：山田 太郎")
    
    participants_count = st.number_input(
        "参加人数（必須）", min_value=1, max_value=10, value=1, step=1
    )
    
    phone = st.text_input("電話番号（必須）", placeholder="例：090-1234-5678")
    
    email = st.text_input("メールアドレス（必須）", placeholder="例：example@gmail.com")
    
    remarks = st.text_area(
        "備考・ご質問など（任意）",
        placeholder="お子様の同伴がある場合や、事前に伝えたい点などがあればご記入ください。",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    submit_button = st.form_submit_button(label="送信する", use_container_width=True)

# ------------------------------------------
# フォーム送信処理
# ------------------------------------------
if submit_button:
    # 選択された日時の集計（スプレッドシート用には詳細名称をセット）
    selected_slots = []
    if d1:
        selected_slots.append("8月24日（月）14:00〜 スターバックス インターパークスタジアム店（折り紙でお花づくり）")
    if d2:
        selected_slots.append("8月24日（月）18:00〜 スターバックス インターパークスタジアム店（折り紙でランタン制作）")
    if d3:
        selected_slots.append("8月25日（火）10:00〜 スターバックス 宇都宮川田店（折り紙でお花づくり）")

    # バリデーションチェック
    errors = []
    
    if not selected_slots:
        errors.append("参加をご希望の日時を少なくとも1つ選択してください。")
    if not name.strip():
        errors.append("お名前を入力してください。")
    if not phone.strip():
        errors.append("電話番号を入力してください。")
    if not email.strip():
        errors.append("メールアドレスを入力してください。")
    elif not re.match(r"^[^@]+@[^@]+\.[^@]+$", email.strip()):
        errors.append("有効なメールアドレスの形式で入力してください。")

    if errors:
        for err in errors:
            st.error(err)
    else:
        # データの追加処理
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        slots_str = " / ".join(selected_slots)
        
        row_data = [
            now_str,
            name.strip(),
            participants_count,
            phone.strip(),
            email.strip(),
            slots_str,
            remarks.strip(),
        ]

        with st.spinner("送信中..."):
            success = save_to_google_sheet(row_data)

        if success:
            st.success("🎉 お申し込みが完了いたしました！ご回答ありがとうございます。")
            st.balloons()
