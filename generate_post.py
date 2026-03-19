"""
대한민국 정부 지원사업 블로그 포스팅 자동 생성기 (완전 무료 버전)

비용 구조:
  - AI 글 생성 : Google Gemini 2.5 Flash API  → 완전 무료 (1일 250회 한도)
  - 이미지 검색 : Pexels API                  → 완전 무료 (월 20,000회 한도)
  - 스케줄링   : GitHub Actions               → 완전 무료
  - 이메일 발송 : Gmail SMTP (앱 비밀번호)     → 완전 무료
"""

import os
import json
import re
import requests
import feedparser
from datetime import datetime

# ── 환경변수 ──────────────────────────────────────────────
GEMINI_API_KEY  = os.environ["GEMINI_API_KEY"]   # Google AI Studio에서 무료 발급
PEXELS_API_KEY  = os.environ["PEXELS_API_KEY"]   # Pexels에서 무료 발급
RECIPIENT_EMAIL = os.environ["RECIPIENT_EMAIL"]  # 수신자 이메일

# Gemini API 엔드포인트 (무료 티어 사용)
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)

# ── 공공 RSS 피드 목록 ────────────────────────────────────
RSS_FEEDS = [
    # 중소벤처기업부 공지사항
    "https://www.mss.go.kr/site/smba/ex/bbs/RssReader.do?bbsId=BBSMSTR_000000000179",
    # 고용노동부 보도자료
    "https://www.moel.go.kr/rss/pressRelease.rss",
    # 창업진흥원
    "https://www.kised.or.kr/rss/news.do",
    # K-Startup
    "https://www.k-startup.go.kr/rss/board.do?menuNo=200020",
    # 중소기업진흥공단
    "https://www.sbc.or.kr/rss/SBC_NEWS.xml",
]

# 폴백: RSS 실패 시 사용할 자체 기획 주제 목록
FALLBACK_TOPICS = [
    "2025 소상공인 경영안정자금 지원사업 신청 방법",
    "청년 창업 지원금 자격 요건 및 신청 절차",
    "중소기업 스마트공장 구축 지원사업 안내",
    "여성기업 성장 지원 정책 총정리",
    "농업인 직불금 확대 지원 안내",
    "취업 취약계층 고용장려금 지원 사업",
    "지역 특화산업 육성 지원 프로그램",
    "신재생에너지 설치 보조금 신청 가이드",
    "중장년 재취업 지원 및 직업훈련 프로그램",
    "1인 창업자를 위한 정부 지원 총정리",
]


def fetch_rss_topics(max_items: int = 5) -> list[dict]:
    """RSS 피드에서 최신 지원사업 뉴스를 수집합니다."""
    items = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                link    = entry.get("link", "")
                # 지원사업 관련 키워드 필터링
                keywords = ["지원", "사업", "신청", "모집", "공모", "보조", "융자", "창업", "취업"]
                if any(kw in title for kw in keywords):
                    summary_clean = re.sub(r"<[^>]+>", "", summary)[:300]
                    items.append({
                        "title":   title,
                        "summary": summary_clean,
                        "link":    link,
                        "source":  feed.feed.get("title", url),
                    })
                if len(items) >= max_items:
                    break
        except Exception as e:
            print(f"RSS 수집 오류 ({url}): {e}")
        if len(items) >= max_items:
            break

    if not items:
        print("RSS 수집 실패 → 폴백 주제 사용")
        import random
        topic = random.choice(FALLBACK_TOPICS)
        items = [{"title": topic, "summary": "", "link": "", "source": "자체 기획"}]

    return items[:max_items]


def generate_blog_post_gemini(topic_items: list[dict]) -> dict:
    """
    Google Gemini 2.5 Flash API로 블로그 포스팅을 생성합니다.
    완전 무료 (1일 250회 한도 / 개인 프로젝트에 충분)
    """
    today = datetime.now().strftime("%Y년 %m월 %d일")
    topics_text = "\n".join(
        [f"- [{i['source']}] {i['title']}\n  {i['summary']}" for i in topic_items]
    )

    prompt = f"""당신은 대한민국 정부 지원사업 전문 블로그 작가입니다.
독자는 창업자, 소상공인, 취업 준비생, 중소기업 대표 등 실질적인 정보를 필요로 하는 사람들입니다.

글쓰기 원칙:
- 부드럽고 자연스러운 한국어 어조 (딱딱한 공문체 금지)
- 마크다운 형식 (## 소제목, **볼드**, 목록 등 활용)
- 3,000자 내외 (공백 포함)
- 독자가 실제로 신청·활용할 수 있도록 핵심 정보 중심
- 마지막에 반드시 "📌 신청 TIP" 또는 "💡 이것만 기억하세요" 섹션 포함
- SEO를 고려한 자연스러운 키워드 배치

오늘({today}) 기준 최신 정부 지원사업 정보를 바탕으로 블로그 포스팅을 작성해주세요.

## 참고할 최신 정보
{topics_text}

위 정보 중 가장 독자에게 유익하고 시의성 있는 주제를 선택하거나, 연관 주제들을 묶어서 하나의 완성도 높은 포스팅을 작성해주세요.

응답은 반드시 아래 JSON 형식으로만 해주세요 (마크다운 코드펜스 없이):
{{
  "title": "블로그 포스팅 제목",
  "description": "포스팅 요약 (100자 내외, 이메일 제목 미리보기용)",
  "keywords": ["키워드1", "키워드2", "키워드3"],
  "pexels_query": "Pexels 이미지 검색 영문 키워드 (2-3단어, 예: korea business office)",
  "content": "마크다운 전체 본문 내용"
}}"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature":     0.7,
            "maxOutputTokens": 4096,
        },
    }

    resp = requests.post(
        GEMINI_URL,
        params={"key": GEMINI_API_KEY},
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    # JSON 코드펜스 제거
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$",     "", raw)

    return json.loads(raw)


def fetch_pexels_image(query: str) -> dict | None:
    """
    Pexels API로 관련 이미지를 검색합니다.
    완전 무료 (시간당 200회 / 월 20,000회 한도)
    """
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={
                "query":       query,
                "per_page":    1,
                "orientation": "landscape",
                "size":        "large",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("photos"):
            photo = data["photos"][0]
            return {
                "url":          photo["src"]["large2x"],
                "small_url":    photo["src"]["medium"],
                "alt":          photo.get("alt", query),
                "photographer": photo["photographer"],
                "pexels_url":   photo["url"],
            }
    except Exception as e:
        print(f"Pexels 이미지 검색 오류: {e}")
    return None


def build_email_html(post: dict, image: dict | None) -> str:
    """이메일 HTML 본문을 구성합니다."""
    today_str = datetime.now().strftime("%Y.%m.%d")

    # 마크다운 → 간단 HTML 변환
    content_html = post["content"]
    content_html = re.sub(r"^## (.+)$",  r"<h2>\1</h2>",            content_html, flags=re.MULTILINE)
    content_html = re.sub(r"^### (.+)$", r"<h3>\1</h3>",            content_html, flags=re.MULTILINE)
    content_html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content_html)
    content_html = re.sub(r"^- (.+)$",   r"<li>\1</li>",            content_html, flags=re.MULTILINE)
    content_html = re.sub(r"(<li>.*</li>)", r"<ul>\1</ul>",          content_html, flags=re.DOTALL)
    content_html = re.sub(r"\n\n", r"</p><p>",                       content_html)
    content_html = f"<p>{content_html}</p>"

    image_block = ""
    if image:
        image_block = f"""
        <div style="margin:24px 0;">
          <img src="{image['url']}" alt="{image['alt']}"
               style="width:100%;border-radius:8px;max-height:420px;object-fit:cover;">
          <p style="font-size:12px;color:#999;margin-top:6px;text-align:right;">
            Photo by <a href="{image['pexels_url']}" style="color:#999;">{image['photographer']}</a> on
            <a href="https://www.pexels.com" style="color:#999;">Pexels</a>
          </p>
        </div>"""

    keywords_html = " ".join(
        [f'<span style="background:#e8f4ff;color:#1a6bbf;padding:3px 10px;'
         f'border-radius:20px;font-size:13px;">#{kw}</span>'
         for kw in post.get("keywords", [])]
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f5f7fa;font-family:'Apple SD Gothic Neo',sans-serif;">
  <div style="max-width:680px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08);">

    <!-- 헤더 -->
    <div style="background:linear-gradient(135deg,#1a6bbf,#0d4a8a);padding:32px 40px;">
      <p style="color:rgba(255,255,255,.7);font-size:13px;margin:0 0 8px;">
        📅 {today_str} 발행 예정 원고 &nbsp;|&nbsp; ✨ Powered by Gemini (무료)
      </p>
      <h1 style="color:#fff;font-size:24px;line-height:1.4;margin:0 0 12px;">{post['title']}</h1>
      <p style="color:rgba(255,255,255,.85);font-size:14px;margin:0;">{post['description']}</p>
    </div>

    <!-- 이미지 -->
    {image_block}

    <!-- 키워드 태그 -->
    <div style="padding:0 40px 8px;">
      {keywords_html}
    </div>

    <!-- 본문 -->
    <div style="padding:16px 40px 40px;color:#333;font-size:15px;line-height:1.8;">
      {content_html}
    </div>

    <!-- 푸터 -->
    <div style="background:#f8f9fc;border-top:1px solid #eee;padding:20px 40px;font-size:13px;color:#777;">
      ✉️ 이 메일에는 <strong>마크다운(.md) 원본 파일</strong>이 첨부되어 있습니다.<br>
      블로그 플랫폼(티스토리, 브런치, 워드프레스 등)에 바로 붙여넣기 하세요.<br><br>
      <span style="color:#aaa;font-size:11px;">
        🤖 AI: Google Gemini 2.5 Flash (무료) &nbsp;|&nbsp;
        🖼️ 이미지: Pexels (무료) &nbsp;|&nbsp;
        ⚙️ 자동화: GitHub Actions (무료)
      </span>
    </div>

  </div>
</body>
</html>"""


def save_markdown(post: dict, image: dict | None, output_dir: str = "output") -> str:
    """마크다운 파일로 저장합니다."""
    os.makedirs(output_dir, exist_ok=True)
    date_str  = datetime.now().strftime("%Y%m%d")
    filename  = f"{output_dir}/post_{date_str}.md"

    image_md = ""
    if image:
        image_md = (
            f"![{image['alt']}]({image['url']})\n"
            f"*Photo by [{image['photographer']}]({image['pexels_url']}) on [Pexels](https://www.pexels.com)*\n\n"
        )

    keywords_line = ", ".join([f"`#{kw}`" for kw in post.get("keywords", [])])

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# {post['title']}\n\n")
        f.write(f"> {post['description']}\n\n")
        f.write(f"**태그:** {keywords_line}\n\n")
        f.write("---\n\n")
        f.write(image_md)
        f.write(post["content"])
        f.write(f"\n\n---\n*발행일: {datetime.now().strftime('%Y년 %m월 %d일')}*\n")

    return filename


def main():
    print("=" * 55)
    print(f"🚀 블로그 원고 생성 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("   💸 사용 비용: ₩0 (완전 무료)")
    print("=" * 55)

    # 1. RSS에서 최신 지원사업 정보 수집
    print("\n📡 [1/4] RSS 피드 수집 중...")
    topics = fetch_rss_topics(max_items=5)
    print(f"   → {len(topics)}개 주제 수집 완료")
    for t in topics:
        print(f"   • {t['title'][:50]}...")

    # 2. Gemini로 블로그 포스팅 생성 (무료)
    print("\n✍️  [2/4] Gemini 2.5 Flash로 블로그 포스팅 생성 중...")
    post = generate_blog_post_gemini(topics)
    char_count = len(post["content"])
    print(f"   → 제목: {post['title']}")
    print(f"   → 글자 수: {char_count:,}자")
    print(f"   → 키워드: {', '.join(post.get('keywords', []))}")

    # 3. Pexels 이미지 검색 (무료)
    print("\n🖼️  [3/4] Pexels 이미지 검색 중...")
    image = fetch_pexels_image(post.get("pexels_query", "korea government office"))
    if image:
        print(f"   → 이미지: {image['alt']} (by {image['photographer']})")
    else:
        print("   → 이미지를 찾지 못했습니다. 텍스트만 발송합니다.")

    # 4. 마크다운 저장
    print("\n💾 [4/4] 마크다운 파일 저장 중...")
    md_file = save_markdown(post, image)
    print(f"   → 저장 완료: {md_file}")

    # 5. 이메일 발송
    print("\n📧 이메일 발송 중...")
    from send_email import send_blog_email
    html_body = build_email_html(post, image)
    send_blog_email(
        recipient=RECIPIENT_EMAIL,
        subject=f"[블로그 원고] {post['title']} ({datetime.now().strftime('%Y.%m.%d')})",
        html_body=html_body,
        attachment_path=md_file,
    )
    print(f"   → {RECIPIENT_EMAIL} 으로 발송 완료!")
    print("\n✅ 전체 파이프라인 완료! (총 비용: ₩0)")


if __name__ == "__main__":
    main()
