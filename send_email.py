"""
Gmail 이메일 발송 모듈
Gmail MCP 또는 SMTP를 통해 블로그 원고를 이메일로 발송합니다.
"""

import os
import smtplib
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path


def send_blog_email(
    recipient: str,
    subject: str,
    html_body: str,
    attachment_path: str | None = None,
) -> bool:
    """
    Gmail SMTP를 통해 이메일을 발송합니다.

    필요한 환경변수:
    - GMAIL_USER     : 발신 Gmail 주소 (예: yourname@gmail.com)
    - GMAIL_APP_PASS : Gmail 앱 비밀번호 (16자리, 2단계 인증 필요)
    """
    gmail_user = os.environ["GMAIL_USER"]
    gmail_pass = os.environ["GMAIL_APP_PASS"]

    # 멀티파트 메일 구성
    msg = MIMEMultipart("mixed")
    msg["From"]    = f"블로그 자동화 <{gmail_user}>"
    msg["To"]      = recipient
    msg["Subject"] = subject

    # HTML 본문
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # 마크다운 파일 첨부
    if attachment_path and Path(attachment_path).exists():
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        filename = Path(attachment_path).name
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{filename}"',
        )
        msg.attach(part)

    # SMTP 발송
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, recipient, msg.as_string())
        print(f"✅ 이메일 발송 성공 → {recipient}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ Gmail 인증 실패: GMAIL_USER / GMAIL_APP_PASS 환경변수를 확인하세요.")
        print("   앱 비밀번호 발급: https://myaccount.google.com/apppasswords")
        raise
    except Exception as e:
        print(f"❌ 이메일 발송 실패: {e}")
        raise


if __name__ == "__main__":
    # 테스트 발송
    recipient = os.environ.get("RECIPIENT_EMAIL", "test@example.com")
    send_blog_email(
        recipient=recipient,
        subject="[테스트] 블로그 자동화 이메일 발송 테스트",
        html_body="<h1>테스트 메일입니다</h1><p>발송 시스템이 정상 작동합니다.</p>",
    )
