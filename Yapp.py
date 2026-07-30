import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- ページ設定 ---
st.set_page_config(page_title="イベント予約・キャンセル受付", page_icon="📝")

SPREADSHEET_NAME = "イベント予約一覧"  # Googleスプレッドシートのファイル名

# ★ 担当者様のお問い合わせ先メールアドレスに書き換えてください
CONTACT_EMAIL = "担当者@example.com" 

# ★ アプリのURLを設定済みです
APP_URL = "https://8zzzhcibve6lr2r2k4pvfj.streamlit.app/"

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

# --- メール送信関数（共通） ---
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

# --- メイン画面（タブ切り替え） ---
st.title("📝 イベント受付システム")

tab1, tab2 = st.tabs(["📝 予約フォーム", "❌ キャンセル受付"])

# ==========================================
# タブ1: 予約フォーム
# ==========================================
with tab1:
    st.write("ご希望の日時（複数選択可）を選択し、必要事項を入力して「予約を確定する」を押してください。")

    dates_options = [
        "8月24日 14:00〜",
        "8月24日 18:00〜",
        "8月25日 14:00〜",
        "8月25日 18:00〜"
    ]

    selected_dates = st.multiselect(
        "参加希望日時を選んでください（複数選択できます）*", 
        options=dates_options
    )

    st.markdown("---")

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

    if submit_button:
        if not selected_dates:
            st.warning("⚠️ 参加希望日時を少なくとも1つ選択してください。")
        elif not name or not email or not phone:
            st.warning("⚠️ お名前、メールアドレス、電話番号は必須項目です。")
        elif "@" not in email or "." not in email:
            st.warning("⚠️ 有効なメールアドレスの形式で入力してください。")
        elif not agree:
            st.warning("⚠️ 予約を確定するには「注意事項」への同意チェックが必要です。")
        else:
            try:
                ws = get_worksheet()
                
                dates_formatted = "、\n".join(selected_dates)
                dates_single_line = "、".join(selected_dates)
                
                # スプレッドシートに保存（最後尾に「確定」ステータスを追加）
                ws.append_row([name, email, phone, num_people, source, dates_single_line, note, "確定"])
                
                # 確認メール送信
                subject = "【予約完了】イベント参加予約を受け付けました"
                body = f"""{name} 様

この度はイベントにお申し込みいただき、誠にありがとうございます。
以下の内容でご予約を承りました。

----------------------------------------
■ ご予約日時：
{dates_formatted}

■ ご予約人数（各回）：{num_people}
----------------------------------------

【キャンセル・ご予約内容の変更】
万が一キャンセルされる場合は、以下のWebサイトよりお手続きをお願いいたします。
👉 {APP_URL}

【お問い合わせ】
ご不明な点がございましたら、以下のアドレスまでご連絡ください。
お問い合わせ先：{CONTACT_EMAIL}

当日のご参加を心よりお待ちしております。
"""
                send_email(email, subject, body)
                
                st.balloons()
                st.success(f"🎉 {name} 様（{num_people}）、ご予約が完了しました！")
                st.info(f"✉️ ご予約確認メールを送信しました。ご質問等は {CONTACT_EMAIL} までお問い合わせください。")
                st.write(f"**確定日時:** {dates_single_line}")
                st.cache_resource.clear()
            except Exception as e:
                st.error(f"⚠️ 保存エラーが発生しました: {e}")

# ==========================================
# タブ2: キャンセル受付
# ==========================================
with tab2:
    st.subheader("❌ ご予約のキャンセル")
    st.write("ご予約時に入力した「お名前」と「メールアドレス」を入力してください。")
    
    with st.form("cancel_form"):
        cancel_name = st.text_input("お名前（フルネーム）*", placeholder="例: 山田 太郎")
        cancel_email = st.text_input("メールアドレス*", placeholder="例: example@email.com")
        
        cancel_submit = st.form_submit_button("予約をキャンセルする")
        
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
                    # 名前とメールアドレスが一致する行を検索
                    if len(row) >= 2 and row[0].strip() == cancel_name.strip() and row[1].strip() == cancel_email.strip():
                        # 現在のステータスチェック（すでにキャンセル済みでないか）
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
