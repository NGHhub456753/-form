import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

# --- メール送信関数 ---
def send_confirmation_email(to_email, name, date_str, people_str):
    try:
        sender_email = st.secrets["smtp"]["email"]
        sender_password = st.secrets["smtp"]["password"]

        subject = "【予約完了】イベント参加予約を受け付けました"
        body = f"""{name} 様

この度はイベントにお申し込みいただき、誠にありがとうございます。
以下の内容でご予約を承りました。

----------------------------------------
■ ご予約日時：{date_str}
■ ご予約人数：{people_str}
----------------------------------------

当日のご参加を心よりお待ちしております。
キャンセルやご変更がございましたら、本メールへの返信にてご連絡ください。
"""

        msg = MIMEMultipart()
        msg["From"] = f"イベント事務局 <{sender_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Gmail SMTPサーバーに接続して送信
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.warning(f"⚠️ 予約は完了しましたが、確認メールの送信に失敗しました: {e}")
        return False

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
    name = st.text_input("お名前（フルネーム）*", placeholder="例: 山田 太郎")
    email = st.text_input("メールアドレス*", placeholder="例: example@email.com")
    phone = st.text_input("電話番号*", placeholder="例: 09012345678（ハイフンなし）")
    
    num_people = st.selectbox(
        "参加人数*",
        options=["1名", "2名", "3名", "4名", "5名以上（備考欄にご記入ください）"]
    )
    
    source = st.selectbox(
        "このイベントをどこで知りましたか？",
        options=["SNS（Instagram/X等）", "知人・友人の紹介", "チラシ・ポスター", "その他"]
    )
    
    note = st.text_area("ご質問・ご要望（任意）", placeholder="配慮事項や、複数人でお越しの際のご連絡などがあればご記入ください")
    
    st.markdown("---")
    agree = st.checkbox("【注意事項】当日のキャンセルは前日までにご連絡ください。上記内容に同意して予約します。")
    
    submit_button = st.form_submit_button("予約を確定する")

# --- 送信時の処理 ---
if submit_button:
    if not name or not email or not phone:
        st.warning("⚠️ お名前、メールアドレス、電話番号は必須項目です。")
    elif "@" not in email or "." not in email:
        st.warning("⚠️ 有効なメールアドレスの形式で入力してください。")
    elif not agree:
        st.warning("⚠️ 予約を確定するには「注意事項」への同意チェックが必要です。")
    else:
        try:
            ws = get_worksheet()
            # スプレッドシートに [名前, メールアドレス, 電話番号, 参加人数, きっかけ, 希望日時, 備考] の順で保存
            ws.append_row([name, email, phone, num_people, source, selected_date, note])
            
            # 自動返信メールの送信
            send_confirmation_email(email, name, selected_date, num_people)
            
            st.balloons()
            st.success(f"🎉 {name} 様（{num_people}）、ご予約が完了しました！")
            st.info("✉️ ご入力いただいたメールアドレスに予約確認メールを送信しました。")
            st.write(f"**確定日時:** {selected_date}")
            st.cache_resource.clear()  # キャッシュをクリア
        except Exception as e:
            st.error(f"⚠️ 保存エラーが発生しました: {e}")
