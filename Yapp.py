import streamlit as st
import pandas as pd
import os

# --- ページ設定 ---
st.set_page_config(page_title="イベント予約システム", page_icon="📝")

st.title("📝 イベント参加予約フォーム")
st.write("ご希望の日時を選択し、必要事項を入力して「予約する」を押してください。")

# --- 定員設定データ（例: 各回10名まで） ---
CAPACITY = 10

# 予約データを保持するファイル
DATA_FILE = "bookings.csv"

# 既存の予約数をカウントする関数
def get_booking_count(selected_date):
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        return len(df[df["希望日時"] == selected_date])
    return 0

# --- メイン画面：日時選択 ---
dates = ["8月10日(月) 10:00〜", "8月10日(月) 14:00〜", "8月11日(火) 10:00〜"]
selected_date = st.selectbox("参加希望日時を選んでください", dates)

# 残り枠数の計算
current_count = get_booking_count(selected_date)
remaining_seats = CAPACITY - current_count

# 残り枠数に応じた表示
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
    
    # 満席の場合はボタンを押せないように判定
    submit_button = st.form_submit_button("予約を確定する", disabled=(remaining_seats <= 0))

# --- 送信時の処理 ---
if submit_button:
    # 簡易バリデーション（入力チェック）
    if not name or not email:
        st.warning("⚠️ お名前とメールアドレスは必須項目です。")
    elif "@" not in email or "." not in email:
        st.warning("⚠️ 有効なメールアドレスの形式で入力してください。")
    else:
        # 予約データを保存
        new_booking = pd.DataFrame([{
            "お名前": name,
            "メールアドレス": email,
            "希望日時": selected_date,
            "備考": note
        }])
        
        if os.path.exists(DATA_FILE):
            new_booking.to_csv(DATA_FILE, mode='a', header=False, index=False)
        else:
            new_booking.to_csv(DATA_FILE, index=False)
            
        st.balloons()  # お祝いの紙吹雪アニメーション🎉
        st.success(f"🎉 {name} 様、ご予約が完了しました！")
        st.write(f"**確定日時:** {selected_date}")
        st.write("ご指定のメールアドレスへ確認通知を送信しました（※シミュレーション）。")
