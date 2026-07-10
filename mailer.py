"""
이메일 발송 모듈 — Gmail SMTP
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from config import GMAIL_USER, GMAIL_APP_PASS


def build_html(post_data, image):
    """HTML 이메일 본문을 생성합니다."""
    from datetime import datetime
    import re

    today_str = datetime.now().strftime("%Y.%m.%d")
    support   = post_data["support_info"]
    meta      = post_data["meta"]
    content   = post_data["content"]

    # 마크다운 → HTML 간단 변환
    c = content
    c = re.sub(r"^## (.+)$",     r"<h2>\1</h2>",         c, flags=re.MULTILINE)
    c = re.sub(r"^### (.+)$",    r"<h3>\1</h3>",         c, flags=re.MULTILINE)
    c = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", c)
    c = re.sub(r"^> (.+)$",      r"<blockquote>\1</blockquote>", c, flags=re.MULTILINE)
    c = re.sub(r"^- (.+)$",      r"<li>\1</li>",         c, flags=re.MULTILINE)
    c = re.sub(r"\n\n",          "</p><p>",               c)
    c = "<p>" + c + "</p>"

    # 이미지
    image_block = ""
    if image:
        image_block = (
            '<div style="margin:24px 0;">'
            '<img src="' + image["url"] + '" alt="' + image["alt"] + '" '
            'style="width:100%;border-radius:8px;max-height:420px;object-fit:cover;">'
            '<p style="font-size:12px;color:#999;margin-top:6px;text-align:right;">'
            'Photo by <a href="' + image["pexels_url"] + '" style="color:#999;">'
            + image["photographer"] + '</a>'
            ' on <a href="https://www.pexels.com" style="color:#999;">Pexels</a></p></div>'
        )

    # 키워드
    kw_html = " ".join(
        '<span style="background:#e8f4ff;color:#1a6bbf;padding:3px 10px;'
        'border-radius:20px;font-size:13px;">#' + kw + '</span>'
        for kw in meta.get("keywords", [])
    )

    # 지원사업 요약 카드
    info_rows = ""
    for label, key in [("주관기관", "agency"), ("지원대상", "target"),
                       ("지원내용", "benefit"), ("신청기간", "period"),
                       ("신청방법", "how_to_apply"), ("문의처", "contact")]:
        val = support.get(key, "확인 필요")
        if val and val != "확인 필요":
            info_rows += (
                '<tr><td style="padding:8px 12px;font-weight:bold;color:#555;'
                'background:#f8f9fc;white-space:nowrap;border:1px solid #eee;">'
                + label + '</td>'
                '<td style="padding:8px 12px;border:1px solid #eee;">' + val + '</td></tr>'
            )

    info_card = ""
    if info_rows:
        info_card = (
            '<div style="margin:24px 0;border-radius:8px;overflow:hidden;">'
            '<table style="width:100%;border-collapse:collapse;font-size:14px;">'
            + info_rows + '</table></div>'
        )

    return (
        '<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"></head>'
        '<body style="margin:0;padding:0;background:#f5f7fa;font-family:sans-serif;">'
        '<div style="max-width:680px;margin:0 auto;background:#fff;border-radius:12px;'
        'overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08);">'

        # 헤더
        '<div style="background:linear-gradient(135deg,#1a6bbf,#0d4a8a);padding:32px 40px;">'
        '<p style="color:rgba(255,255,255,.7);font-size:13px;margin:0 0 8px;">'
        '📅 ' + today_str + ' 발행 예정 원고 | ✨ Gemini 2.5 Flash-Lite (무료)</p>'
        '<h1 style="color:#fff;font-size:24px;line-height:1.4;margin:0 0 12px;">'
        + meta.get("blog_title", support.get("title", "")) + '</h1>'
        '<p style="color:rgba(255,255,255,.85);font-size:14px;margin:0;">'
        + meta.get("description", "") + '</p></div>'

        # 이미지
        + image_block +

        # 지원사업 요약 카드
        '<div style="padding:0 40px;">' + info_card + '</div>'

        # 키워드
        '<div style="padding:0 40px 8px;">' + kw_html + '</div>'

        # 본문
        '<div style="padding:8px 40px 40px;color:#333;font-size:15px;line-height:1.8;">' + c + '</div>'

        # 푸터
        '<div style="background:#f8f9fc;border-top:1px solid #eee;padding:20px 40px;font-size:13px;color:#777;">'
        '✉️ 마크다운(.md) 파일이 첨부되어 있습니다.<br>'
        '<span style="color:#aaa;font-size:11px;">'
        '🤖 Gemini 2.5 Flash-Lite | 🖼️ Pexels | ⚙️ GitHub Actions</span>'
        '</div></div></body></html>'
    )


def send_email(recipient, subject, html_body, attachment_path=None):
    """Gmail SMTP로 이메일을 발송합니다."""
    msg = MIMEMultipart("mixed")
    msg["From"]    = "블로그 자동화 <" + GMAIL_USER + ">"
    msg["To"]      = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    if attachment_path and Path(attachment_path).exists():
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            'attachment; filename="' + Path(attachment_path).name + '"',
        )
        msg.attach(part)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASS)
            server.sendmail(GMAIL_USER, recipient, msg.as_string())
        print("✅ 이메일 발송 성공 → " + recipient)
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ Gmail 인증 실패 — GMAIL_USER / GMAIL_APP_PASS 확인")
        raise
    except Exception as e:
        print("❌ 이메일 발송 실패: " + str(e))
        raise
