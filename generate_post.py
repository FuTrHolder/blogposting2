"""
대한민국 정부 지원사업 블로그 포스팅 자동 생성기 (완전 무료 버전)

AI    : Google Gemini 2.0 Flash  (무료, 1일 1,500회)
이미지 : Pexels API               (무료, 월 20,000회)
스케줄 : GitHub Actions           (무료)
메일  : Gmail SMTP                (무료)
"""

import os, json, re, random, requests, feedparser
from datetime import datetime

GEMINI_API_KEY  = os.environ["GEMINI_API_KEY"]
PEXELS_API_KEY  = os.environ["PEXELS_API_KEY"]
RECIPIENT_EMAIL = os.environ["RECIPIENT_EMAIL"]

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

RSS_FEEDS = [
    "https://www.mss.go.kr/site/smba/ex/bbs/RssReader.do?bbsId=BBSMSTR_000000000179",
    "https://www.moel.go.kr/rss/pressRelease.rss",
    "https://www.kised.or.kr/rss/news.do",
    "https://www.k-startup.go.kr/rss/board.do?menuNo=200020",
    "https://www.sbc.or.kr/rss/SBC_NEWS.xml",
]

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

# ── RSS 수집 ──────────────────────────────────────────────

def fetch_rss_topics(max_items=5):
    items = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                link    = entry.get("link", "")
                kws = ["지원","사업","신청","모집","공모","보조","융자","창업","취업"]
                if any(kw in title for kw in kws):
                    summary_clean = re.sub(r"<[^>]+>", "", summary)[:300]
                    items.append({
                        "title": title, "summary": summary_clean,
                        "link": link, "source": feed.feed.get("title", url),
                    })
                if len(items) >= max_items:
                    break
        except Exception as e:
            print(f"RSS 수집 오류: {e}")
        if len(items) >= max_items:
            break

    if not items:
        print("RSS 수집 실패 → 폴백 주제 사용")
        topic = random.choice(FALLBACK_TOPICS)
        items = [{"title": topic, "summary": "", "link": "", "source": "자체 기획"}]

    return items[:max_items]

# ── Gemini 호출 ───────────────────────────────────────────

def _call_gemini(prompt, max_tokens=8192, temperature=0.7):
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    resp = requests.post(
        GEMINI_URL,
        params={"key": GEMINI_API_KEY},
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()

    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("Gemini 응답 없음: " + str(data.get("promptFeedback", {})))

    finish_reason = candidates[0].get("finishReason", "STOP")
    parts = candidates[0].get("content", {}).get("parts", [])

    if not parts or not parts[0].get("text", "").strip():
        raise ValueError("Gemini 텍스트 없음 (finishReason=" + finish_reason + ")")

    text = parts[0]["text"].strip()
    if finish_reason == "MAX_TOKENS":
        print("   ⚠️  MAX_TOKENS 종료 — 출력 텍스트 그대로 사용 (" + str(len(text)) + "자)")

    return text

# ── 블로그 생성 (2단계) ───────────────────────────────────

def generate_blog_post_gemini(topic_items):
    today = datetime.now().strftime("%Y년 %m월 %d일")

    topics_lines = []
    for i in topic_items:
        topics_lines.append("- [" + i["source"] + "] " + i["title"])
        if i["summary"]:
            topics_lines.append("  " + i["summary"])
    topics_text = "\n".join(topics_lines)

    # JSON 템플릿 — f-string 밖에서 일반 문자열로 정의
    json_template = (
        '{"title":"매력적인 제목",'
        '"description":"요약 80자 이내",'
        '"keywords":["키워드1","키워드2","키워드3","키워드4","키워드5"],'
        '"pexels_query":"english 2words",'
        '"outline":["소제목1","소제목2","소제목3","소제목4","소제목5"]}'
    )

    # ── 1단계: 메타데이터 JSON ───────────────────────────
    meta_prompt = "\n".join([
        "당신은 대한민국 정부 지원사업 전문 블로그 기획자입니다.",
        "오늘(" + today + ") 기준 아래 최신 정보를 참고해 포스팅 기획안을 JSON으로 만들어주세요.",
        "",
        "참고 정보:",
        topics_text,
        "",
        "출력 규칙:",
        "- 반드시 아래 JSON 형식만 출력 (앞뒤 설명, 코드펜스 절대 금지)",
        "- 모든 값은 한국어 (pexels_query만 영어 2단어)",
        "",
        json_template,
    ])

    meta = None
    for attempt in range(1, 4):
        try:
            raw = _call_gemini(meta_prompt, max_tokens=2048, temperature=0.7)
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"\s*```\s*$",       "", raw, flags=re.MULTILINE)
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                raise ValueError("JSON 블록 없음")
            meta = json.loads(m.group())
            print("   → [1단계] 메타데이터 생성 완료 (시도 " + str(attempt) + "회)")
            break
        except (json.JSONDecodeError, ValueError) as e:
            print("   ⚠️  [1단계] 시도 " + str(attempt) + "/3 실패: " + str(e))
            if attempt == 3:
                raise RuntimeError("메타데이터 생성 3회 모두 실패") from e

    # ── 2단계: 마크다운 본문 ─────────────────────────────
    outline_lines = []
    for idx, h in enumerate(meta.get("outline", [])):
        outline_lines.append(str(idx + 1) + ". " + h)
    outline_text = "\n".join(outline_lines)

    content_prompt = "\n".join([
        "당신은 대한민국 정부 지원사업 전문 블로그 작가입니다.",
        "",
        "제목: " + meta["title"],
        "",
        "아래 소제목 순서대로 블로그 본문을 작성해주세요:",
        outline_text,
        "",
        "작성 원칙:",
        "- 부드럽고 자연스러운 한국어 (공문체 금지)",
        "- 마크다운 형식 (## 소제목, **볼드**, - 목록 적극 활용)",
        "- 전체 2,800자 ~ 3,200자 (공백 포함)",
        "- 독자가 직접 신청할 수 있도록 구체적인 정보 포함",
        "- 마지막 섹션 제목은 반드시 '📌 신청 TIP' 또는 '💡 이것만 기억하세요'",
        "- 코드펜스나 JSON 없이 마크다운 텍스트만 출력",
        "",
        "지금 바로 본문만 작성하세요:",
    ])

    content = None
    for attempt in range(1, 4):
        try:
            raw = _call_gemini(content_prompt, max_tokens=8192, temperature=0.75)
            raw = re.sub(r"^```(?:markdown)?\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"\s*```\s*$",           "", raw, flags=re.MULTILINE)
            raw = raw.strip()
            if len(raw) < 800:
                raise ValueError("본문 너무 짧음 (" + str(len(raw)) + "자)")
            content = raw
            print("   → [2단계] 본문 생성 완료 (" + str(len(content)) + "자, 시도 " + str(attempt) + "회)")
            break
        except ValueError as e:
            print("   ⚠️  [2단계] 시도 " + str(attempt) + "/3 실패: " + str(e))
            if attempt == 3:
                raise RuntimeError("본문 생성 3회 모두 실패") from e

    return {
        "title":        meta["title"],
        "description":  meta["description"],
        "keywords":     meta.get("keywords", []),
        "pexels_query": meta.get("pexels_query", "korea government support"),
        "content":      content,
    }

# ── Pexels 이미지 ─────────────────────────────────────────

def fetch_pexels_image(query):
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": 1, "orientation": "landscape", "size": "large"},
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
        print("Pexels 오류: " + str(e))
    return None

# ── 이메일 HTML ───────────────────────────────────────────

def build_email_html(post, image):
    today_str = datetime.now().strftime("%Y.%m.%d")

    c = post["content"]
    c = re.sub(r"^## (.+)$",     r"<h2>\1</h2>",         c, flags=re.MULTILINE)
    c = re.sub(r"^### (.+)$",    r"<h3>\1</h3>",         c, flags=re.MULTILINE)
    c = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", c)
    c = re.sub(r"^- (.+)$",      r"<li>\1</li>",         c, flags=re.MULTILINE)
    c = re.sub(r"\n\n",          "</p><p>",               c)
    c = "<p>" + c + "</p>"

    image_block = ""
    if image:
        image_block = (
            '<div style="margin:24px 0;">'
            '<img src="' + image["url"] + '" alt="' + image["alt"] + '" '
            'style="width:100%;border-radius:8px;max-height:420px;object-fit:cover;">'
            '<p style="font-size:12px;color:#999;margin-top:6px;text-align:right;">'
            'Photo by <a href="' + image["pexels_url"] + '" style="color:#999;">' + image["photographer"] + '</a>'
            ' on <a href="https://www.pexels.com" style="color:#999;">Pexels</a></p></div>'
        )

    kw_html = " ".join(
        '<span style="background:#e8f4ff;color:#1a6bbf;padding:3px 10px;'
        'border-radius:20px;font-size:13px;">#' + kw + '</span>'
        for kw in post.get("keywords", [])
    )

    return (
        '<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"></head>'
        '<body style="margin:0;padding:0;background:#f5f7fa;font-family:sans-serif;">'
        '<div style="max-width:680px;margin:0 auto;background:#fff;border-radius:12px;'
        'overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08);">'
        '<div style="background:linear-gradient(135deg,#1a6bbf,#0d4a8a);padding:32px 40px;">'
        '<p style="color:rgba(255,255,255,.7);font-size:13px;margin:0 0 8px;">'
        '📅 ' + today_str + ' 발행 예정 원고 | ✨ Gemini 2.0 Flash (무료)</p>'
        '<h1 style="color:#fff;font-size:24px;line-height:1.4;margin:0 0 12px;">' + post["title"] + '</h1>'
        '<p style="color:rgba(255,255,255,.85);font-size:14px;margin:0;">' + post["description"] + '</p>'
        '</div>'
        + image_block +
        '<div style="padding:16px 40px 8px;">' + kw_html + '</div>'
        '<div style="padding:8px 40px 40px;color:#333;font-size:15px;line-height:1.8;">' + c + '</div>'
        '<div style="background:#f8f9fc;border-top:1px solid #eee;padding:20px 40px;font-size:13px;color:#777;">'
        '✉️ 마크다운(.md) 파일이 첨부되어 있습니다.<br>'
        '<span style="color:#aaa;font-size:11px;">🤖 Gemini 2.0 Flash | 🖼️ Pexels | ⚙️ GitHub Actions</span>'
        '</div></div></body></html>'
    )

# ── 마크다운 저장 ─────────────────────────────────────────

def save_markdown(post, image, output_dir="output"):
    os.makedirs(output_dir, exist_ok=True)
    filename = output_dir + "/post_" + datetime.now().strftime("%Y%m%d") + ".md"
    image_md = ""
    if image:
        image_md = (
            "![" + image["alt"] + "](" + image["url"] + ")\n"
            "*Photo by [" + image["photographer"] + "](" + image["pexels_url"] + ")"
            " on [Pexels](https://www.pexels.com)*\n\n"
        )
    kw_line = ", ".join("`#" + kw + "`" for kw in post.get("keywords", []))
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# " + post["title"] + "\n\n")
        f.write("> " + post["description"] + "\n\n")
        f.write("**태그:** " + kw_line + "\n\n---\n\n")
        f.write(image_md)
        f.write(post["content"])
        f.write("\n\n---\n*발행일: " + datetime.now().strftime("%Y년 %m월 %d일") + "*\n")
    return filename

# ── 메인 ─────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("🚀 블로그 원고 생성 시작: " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("   💸 사용 비용: 0원 (완전 무료)")
    print("=" * 55)

    print("\n📡 [1/4] RSS 피드 수집 중...")
    topics = fetch_rss_topics(max_items=5)
    print("   → " + str(len(topics)) + "개 주제 수집 완료")
    for t in topics:
        print("   • " + t["title"][:50] + "...")

    print("\n✍️  [2/4] Gemini 2.0 Flash로 블로그 포스팅 생성 중...")
    post = generate_blog_post_gemini(topics)
    print("   → 제목: " + post["title"])
    print("   → 글자 수: " + str(len(post["content"])) + "자")
    print("   → 키워드: " + ", ".join(post.get("keywords", [])))

    print("\n🖼️  [3/4] Pexels 이미지 검색 중...")
    image = fetch_pexels_image(post.get("pexels_query", "korea government office"))
    if image:
        print("   → " + image["alt"] + " (by " + image["photographer"] + ")")
    else:
        print("   → 이미지 없음. 텍스트만 발송합니다.")

    print("\n💾 [4/4] 마크다운 파일 저장 중...")
    md_file = save_markdown(post, image)
    print("   → 저장 완료: " + md_file)

    print("\n📧 이메일 발송 중...")
    from send_email import send_blog_email
    send_blog_email(
        recipient=RECIPIENT_EMAIL,
        subject="[블로그 원고] " + post["title"] + " (" + datetime.now().strftime("%Y.%m.%d") + ")",
        html_body=build_email_html(post, image),
        attachment_path=md_file,
    )
    print("   → " + RECIPIENT_EMAIL + " 으로 발송 완료!")
    print("\n✅ 전체 파이프라인 완료! (총 비용: 0원)")


if __name__ == "__main__":
    main()
