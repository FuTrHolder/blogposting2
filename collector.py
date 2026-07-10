"""
수집 모듈 — RSS 피드 + 공고 원문 수집
"""
import re
import random
import requests
import feedparser
from config import RSS_FEEDS, FALLBACK_TOPICS


def fetch_rss_candidates(max_items=10):
    """
    RSS 피드에서 오늘의 지원사업 후보를 수집합니다.
    반환: [{"title", "summary", "link", "source", "category"}]
    """
    items = []
    keywords = ["지원", "사업", "신청", "모집", "공모", "보조", "융자", "창업", "취업", "복지", "주거", "청년"]

    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            source_name = feed.feed.get("title", url)
            for entry in feed.entries[:5]:
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                link    = entry.get("link", "")
                if any(kw in title for kw in keywords):
                    summary_clean = re.sub(r"<[^>]+>", "", summary)[:400]
                    items.append({
                        "title":    title,
                        "summary":  summary_clean,
                        "link":     link,
                        "source":   source_name,
                        "category": _guess_category(title),
                    })
            if len(items) >= max_items:
                break
        except Exception as e:
            print("RSS 수집 오류 (" + url + "): " + str(e))

    if not items:
        print("RSS 수집 실패 → 폴백 주제 사용")
        chosen = random.choice(FALLBACK_TOPICS)
        items = [{
            "title":    chosen["title"],
            "summary":  "",
            "link":     "",
            "source":   chosen["agency"],
            "category": chosen["category"],
        }]

    return items[:max_items]


def fetch_article_text(url, max_chars=3000):
    """
    공고 원문 URL에서 텍스트를 가져옵니다.
    실패 시 빈 문자열 반환.
    """
    if not url:
        return ""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        # HTML 태그 제거
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception as e:
        print("원문 수집 오류 (" + str(url) + "): " + str(e))
        return ""


def _guess_category(title):
    """제목 키워드로 카테고리를 추정합니다."""
    mapping = {
        "청년": "청년",
        "창업": "창업",
        "취업": "취업·고용",
        "고용": "취업·고용",
        "복지": "복지",
        "주거": "주거",
        "소상공인": "소상공인",
        "중소기업": "중소기업",
        "스마트": "기술·제조",
        "에너지": "환경·에너지",
        "여성": "여성",
        "장애": "복지·장애",
        "농업": "농업",
    }
    for kw, cat in mapping.items():
        if kw in title:
            return cat
    return "일반지원"
