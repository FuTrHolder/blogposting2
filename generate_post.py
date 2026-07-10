"""
대한민국 정부 지원사업 블로그 포스팅 자동 생성기 v2
완전 무료 | Gemini 2.5 Flash-Lite + Pexels + Gmail + GitHub Actions

[개선된 파이프라인]
1. RSS/폴백으로 오늘의 후보 수집
2. 공고 원문 수집 (가능한 경우)
3. AI로 핵심 정보 구조화 (JSON)
4. FAQ 자동 생성
5. 관련 지원사업 추천
6. 정책 배경 생성
7. 9단계 고정 템플릿으로 본문 작성
8. SEO 메타데이터 생성
9. Pexels 이미지 검색
10. 마크다운 저장 + 이메일 발송
"""

import os
import re
import requests
from datetime import datetime
from pathlib import Path

# 모듈 임포트
from config import RECIPIENT_EMAIL, PEXELS_API_KEY
from collector import fetch_rss_candidates, fetch_article_text
from analyzer import extract_support_info, generate_faq, find_related_programs, generate_policy_background
from writer import build_meta, write_post
from mailer import build_html, send_email


# ── Pexels 이미지 검색 ────────────────────────────────────

def fetch_pexels_image(query):
    """Pexels API로 관련 이미지를 검색합니다. 완전 무료 (월 20,000회)"""
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


# ── 마크다운 저장 ─────────────────────────────────────────

def save_markdown(post_data, image, output_dir="output"):
    """포스팅을 마크다운 파일로 저장합니다."""
    os.makedirs(output_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    filename = output_dir + "/post_" + date_str + ".md"

    support = post_data["support_info"]
    meta    = post_data["meta"]
    content = post_data["content"]
    faq     = post_data["faq"]
    related = post_data["related"]

    # 이미지 마크다운
    image_md = ""
    if image:
        image_md = (
            "![" + image["alt"] + "](" + image["url"] + ")\n"
            "*Photo by [" + image["photographer"] + "](" + image["pexels_url"] + ")"
            " on [Pexels](https://www.pexels.com)*\n\n"
        )

    # 키워드
    kw_line = ", ".join("`#" + kw + "`" for kw in meta.get("keywords", []))

    with open(filename, "w", encoding="utf-8") as f:
        f.write("# " + meta.get("blog_title", support.get("title", "")) + "\n\n")
        f.write("> " + meta.get("description", "") + "\n\n")
        f.write("**주관기관:** " + support.get("agency", "") + "  \n")
        f.write("**지원대상:** " + support.get("target", "") + "  \n")
        f.write("**신청기간:** " + support.get("period", "") + "  \n")
        f.write("**공식사이트:** " + support.get("official_url", "") + "\n\n")
        f.write("**태그:** " + kw_line + "\n\n---\n\n")
        f.write(image_md)
        f.write(content)
        f.write("\n\n---\n")
        f.write("*발행일: " + datetime.now().strftime("%Y년 %m월 %d일") + " | ")
        f.write("생성: Gemini 2.5 Flash-Lite + Pexels + GitHub Actions*\n")

    return filename


# ── 메인 파이프라인 ───────────────────────────────────────

def main():
    print("=" * 55)
    print("🚀 블로그 원고 생성 시작: " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("   💸 사용 비용: 0원 (완전 무료) | v2 고품질 파이프라인")
    print("=" * 55)

    # ── STEP 1: 후보 수집 ─────────────────────────────────
    print("\n📡 [1/8] RSS 피드에서 오늘의 지원사업 후보 수집 중...")
    candidates = fetch_rss_candidates(max_items=5)
    print("   → " + str(len(candidates)) + "개 후보 수집 완료")
    topic = candidates[0]  # 첫 번째 후보 선택
    print("   → 선택된 주제: " + topic["title"])

    # ── STEP 2: 공고 원문 수집 ────────────────────────────
    print("\n📄 [2/8] 공고 원문 수집 중...")
    article_text = ""
    if topic.get("link"):
        article_text = fetch_article_text(topic["link"])
        if article_text:
            print("   → 원문 수집 완료 (" + str(len(article_text)) + "자)")
        else:
            print("   → 원문 수집 실패 — 요약 정보로 진행")
    else:
        print("   → URL 없음 — 요약 정보로 진행")

    # ── STEP 3: 공고 정보 구조화 ──────────────────────────
    print("\n🔍 [3/8] 공고 핵심 정보 구조화 중...")
    support_info = extract_support_info(topic, article_text)
    print("   → 사업명: " + support_info.get("title", ""))
    print("   → 지원대상: " + support_info.get("target", ""))
    print("   → 지원내용: " + support_info.get("benefit", ""))

    # ── STEP 4: FAQ 생성 ──────────────────────────────────
    print("\n💬 [4/8] FAQ 자동 생성 중...")
    faq = generate_faq(support_info)

    # ── STEP 5: 관련 지원사업 추천 ───────────────────────
    print("\n🔗 [5/8] 관련 지원사업 추천 중...")
    related = find_related_programs(support_info)

    # ── STEP 6: 정책 배경 생성 ───────────────────────────
    print("\n📋 [6/8] 정책 배경 생성 중...")
    background = generate_policy_background(support_info)

    # ── STEP 7: 본문 + 메타데이터 생성 ───────────────────
    print("\n✍️  [7/8] 고품질 블로그 본문 작성 중...")
    meta    = build_meta(support_info, faq, related, background)
    content = write_post(support_info, faq, related, background, meta)
    print("   → 블로그 제목: " + meta.get("blog_title", ""))
    print("   → 글자 수: " + str(len(content)) + "자")
    print("   → 키워드: " + ", ".join(meta.get("keywords", [])))

    # ── STEP 8: 이미지 검색 ──────────────────────────────
    print("\n🖼️  [8/8] Pexels 이미지 검색 중...")
    image = fetch_pexels_image(meta.get("pexels_query", "korea government support"))
    if image:
        print("   → " + image["alt"] + " (by " + image["photographer"] + ")")
    else:
        print("   → 이미지 없음, 텍스트만 발송")

    # ── 저장 & 발송 ───────────────────────────────────────
    post_data = {
        "support_info": support_info,
        "faq":          faq,
        "related":      related,
        "background":   background,
        "meta":         meta,
        "content":      content,
    }

    print("\n💾 마크다운 파일 저장 중...")
    md_file = save_markdown(post_data, image)
    print("   → 저장 완료: " + md_file)

    print("\n📧 이메일 발송 중...")
    html_body = build_html(post_data, image)
    subject = (
        "[블로그 원고] "
        + meta.get("blog_title", support_info.get("title", ""))
        + " (" + datetime.now().strftime("%Y.%m.%d") + ")"
    )
    send_email(
        recipient=RECIPIENT_EMAIL,
        subject=subject,
        html_body=html_body,
        attachment_path=md_file,
    )
    print("   → " + RECIPIENT_EMAIL + " 으로 발송 완료!")
    print("\n✅ 전체 파이프라인 완료! (총 비용: 0원)")


if __name__ == "__main__":
    main()
