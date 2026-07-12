"""
멀티 소스 수집 모듈 v3
============================================================
[배경]
GitHub Actions IP(Microsoft Azure)는 한국 정부·언론·포털 사이트에서
전면 차단(HTTP 403)됩니다. RSS, 크롤링, 네이버/다음 API 모두 불가.

[실제 동작하는 소스 — 우선순위 순]
1. Gemini 웹 검색 Grounding  : Gemini가 직접 웹 검색 → 최신 공고 반환
2. Gemini 날짜 컨텍스트 생성 : 웹검색 실패 시 Gemini 지식 기반 추론
3. 날짜 기반 주제 로테이션   : 30개 주제 풀에서 매일 다른 주제 선택

[GPT 제안 반영]
- 멀티 소스 병렬 시도 (단일 소스 의존 제거)
- 소스별 실패 격리 (한 소스 실패해도 다음으로 자동 전환)
- 중복 제거 및 우선순위 점수화
- 본문 기반 정보 추출 우선 (RSS 요약 의존 제거)
- 매일 다른 주제 보장 (날짜 기반 로테이션)
"""

import re
import json
import time
import random
import requests
import feedparser
from datetime import datetime
from config import GEMINI_API_KEY, GEMINI_MODEL, FALLBACK_TOPICS


# ── 소스 1: Gemini 웹 검색 Grounding ─────────────────────

def _collect_via_gemini_search(max_items=5):
    """
    Gemini google_search grounding으로 오늘 기준 최신 공고를 수집합니다.
    Gemini가 직접 웹을 검색하여 실제 공고 정보를 가져옵니다.
    """
    today = datetime.now().strftime("%Y년 %m월")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + GEMINI_MODEL + ":generateContent"
    )

    # 카테고리 로테이션으로 매일 다른 분야 검색
    categories = [
        "창업·스타트업 지원사업",
        "청년 지원사업 (취업·주거·금융)",
        "소상공인·자영업자 지원사업",
        "중소기업 지원사업",
        "복지·주거 지원사업",
        "취업·고용 지원사업",
        "농업·에너지 지원사업",
    ]
    category = categories[datetime.now().timetuple().tm_yday % len(categories)]

    json_template = (
        '[{"title":"사업명","agency":"주관기관",'
        '"target":"지원대상","benefit":"주요혜택",'
        '"period":"신청기간","category":"분야","link":"공식URL"}]'
    )

    prompt = "\n".join([
        today + " 현재 대한민국 정부에서 운영 중인 [" + category + "] 관련",
        "지원사업 " + str(max_items) + "개를 웹에서 검색하여 알려주세요.",
        "",
        "조건:",
        "- 2025~2026년 현재 신청 가능하거나 곧 시작되는 사업",
        "- 지원금액/혜택이 구체적으로 명시된 사업 우선",
        "- 중앙정부 주관 사업 우선 (지자체 사업도 포함 가능)",
        "- 공식 사이트 URL 포함 (없으면 빈 문자열)",
        "",
        "반드시 JSON 배열만 출력 (코드펜스 없이):",
        json_template,
    ])

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
    }

    wait_times = [20, 40]
    for attempt in range(3):
        try:
            resp = requests.post(
                url,
                params={"key": GEMINI_API_KEY},
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=60,
            )
            if resp.status_code in (429, 500, 503):
                if attempt < len(wait_times):
                    print("   ⏳ " + str(resp.status_code) + " — " + str(wait_times[attempt]) + "초 대기...")
                    time.sleep(wait_times[attempt])
                    continue
                return []
            resp.raise_for_status()

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return []

            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            if not text:
                return []

            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
            text = re.sub(r"\s*```\s*$", "", text, flags=re.MULTILINE)
            m = re.search(r"\[.*\]", text, re.DOTALL)
            if not m:
                return []

            items = json.loads(m.group())
            result = []
            for item in items:
                title = item.get("title", "").strip()
                if not title:
                    continue
                result.append({
                    "title":    title,
                    "summary":  item.get("benefit", item.get("target", "")),
                    "link":     item.get("link", ""),
                    "source":   item.get("agency", "정부기관"),
                    "category": item.get("category", category),
                    "period":   item.get("period", ""),
                    "score":    10,  # 최신 웹 검색 결과 = 최고 점수
                })
            return result[:max_items]

        except (json.JSONDecodeError, ValueError):
            return []
        except Exception as e:
            print("   Gemini 검색 오류: " + str(e)[:60])
            return []
    return []


# ── 소스 2: Gemini 지식 기반 추론 (날짜 컨텍스트) ──────────

def _collect_via_gemini_knowledge(max_items=5):
    """
    Gemini의 학습 데이터 기반으로 현재 운영 중인 주요 지원사업을 추론합니다.
    웹 검색 없이 Gemini 자체 지식을 활용합니다.
    """
    today = datetime.now().strftime("%Y년 %m월 %d일")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + GEMINI_MODEL + ":generateContent"
    )

    # 요일별 카테고리 (월=창업, 화=청년, 수=기업, 목=취업, 금=복지, 토=주거, 일=농업)
    weekday_category = [
        "창업 및 스타트업",
        "청년 지원",
        "중소기업 및 소상공인",
        "취업 및 고용",
        "복지 및 사회보장",
        "주거 및 부동산",
        "농업·에너지·환경",
    ]
    category = weekday_category[datetime.now().weekday()]

    json_template = (
        '[{"title":"사업명","agency":"주관기관","target":"지원대상",'
        '"benefit":"지원내용","period":"신청기간","official_url":"공식URL"}]'
    )

    prompt = "\n".join([
        "오늘은 " + today + "입니다.",
        "대한민국에서 현재 운영 중인 [" + category + "] 분야 정부 지원사업 " + str(max_items) + "개를 알려주세요.",
        "",
        "우선순위:",
        "1. 매년 정기적으로 운영되는 대표 사업",
        "2. 지원 규모가 큰 사업",
        "3. 신청 절차가 명확한 사업",
        "",
        "반드시 JSON 배열만 출력 (코드펜스 없이):",
        json_template,
    ])

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048},
    }

    try:
        resp = requests.post(
            url,
            params={"key": GEMINI_API_KEY},
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s*```\s*$", "", text, flags=re.MULTILINE)
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if not m:
            return []
        items = json.loads(m.group())
        result = []
        for item in items:
            if not item.get("title", "").strip():
                continue
            result.append({
                "title":    item.get("title", "").strip(),
                "summary":  item.get("benefit", ""),
                "link":     item.get("official_url", ""),
                "source":   item.get("agency", "정부기관"),
                "category": category,
                "period":   item.get("period", ""),
                "score":    7,  # 지식 기반 = 중간 점수
            })
        return result[:max_items]
    except Exception as e:
        print("   Gemini 지식 기반 오류: " + str(e)[:60])
        return []


# ── 소스 3: RSS 피드 시도 (부분 성공 가능) ────────────────

def _collect_via_rss(max_items=5):
    """
    RSS 피드 수집 시도. GitHub Actions에서 대부분 403이지만
    간혹 성공하는 경우를 위해 유지합니다.
    """
    from config import RSS_FEEDS
    keywords = ["지원","사업","신청","모집","공모","보조","융자","창업","취업","복지","주거","청년"]
    items = []

    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            if not feed.entries:
                continue
            for entry in feed.entries[:3]:
                title = entry.get("title", "").strip()
                if any(kw in title for kw in keywords):
                    summary = entry.get("summary", entry.get("description", ""))
                    summary_clean = re.sub(r"<[^>]+>", "", summary)[:300]
                    items.append({
                        "title":    title,
                        "summary":  summary_clean,
                        "link":     entry.get("link", ""),
                        "source":   feed.feed.get("title", url),
                        "category": _guess_category(title),
                        "period":   "",
                        "score":    9,  # 실제 RSS = 높은 점수
                    })
            if len(items) >= max_items:
                break
        except Exception:
            pass

    return items[:max_items]


# ── 소스 4: 날짜 기반 주제 로테이션 (최후 보루) ─────────────

def _collect_via_rotation():
    """
    30개 주제 풀에서 날짜 기반으로 매일 다른 주제를 선택합니다.
    모든 소스 실패 시에도 반드시 1개의 주제를 반환합니다.
    """
    topic_pool = [
        # 창업
        ("예비창업패키지 지원사업 신청 방법",              "중소벤처기업부",     "창업"),
        ("초기창업패키지 지원 내용 및 신청 안내",           "중소벤처기업부",     "창업"),
        ("TIPS 프로그램 스타트업 기술창업 지원",            "중소벤처기업부",     "창업·R&D"),
        ("소상공인 경영안정자금 융자 신청 방법",            "소상공인시장진흥공단","소상공인"),
        ("소상공인 성장지원센터 무료 컨설팅 신청",          "소상공인시장진흥공단","소상공인"),
        ("소상공인 폐업지원 희망리턴패키지 신청 안내",      "소상공인시장진흥공단","소상공인"),
        # 청년
        ("청년도약계좌 가입 조건 및 월 최대 70만원 혜택",  "금융위원회",         "청년·금융"),
        ("청년내일저축계좌 신청 방법 및 자격 조건",         "보건복지부",         "청년"),
        ("청년 주거급여 분리지급 신청 안내",                "국토교통부",         "청년·주거"),
        ("청년일자리도약장려금 지원 기업·청년 신청 방법",   "고용노동부",         "청년·취업"),
        # 취업·고용
        ("국민취업지원제도 1유형 구직촉진수당 신청 가이드", "고용노동부",         "취업"),
        ("국민내일배움카드 발급 및 훈련비 지원 안내",       "고용노동부",         "취업"),
        ("고용촉진장려금 신청 방법 및 지원 금액",          "고용노동부",         "취업"),
        ("중장년 새출발크레딧 재취업 지원 프로그램",        "고용노동부",         "중장년·취업"),
        # 중소기업
        ("중소기업 스마트공장 구축 지원사업 신청 방법",     "중소벤처기업부",     "중소기업"),
        ("중소기업 정책자금 융자 종류별 신청 방법 총정리",  "중소기업진흥공단",   "중소기업"),
        ("중소기업 기술개발 R&D 지원사업 공고 안내",       "중소벤처기업부",     "기술·R&D"),
        # 복지
        ("기초생활수급자 생계급여 신청 자격 및 지원금 안내","보건복지부",         "복지"),
        ("장애인 활동지원 서비스 신청 방법 및 지원 내용",  "보건복지부",         "복지·장애"),
        ("한부모가족 복지급여 신청 방법 및 지원 내용",     "여성가족부",         "복지"),
        ("노인 일자리 및 사회활동 지원사업 신청 방법",     "보건복지부",         "노인"),
        # 주거
        ("청년 전세자금대출 종류 및 신청 방법 총정리",     "국토교통부",         "주거"),
        ("주거급여 신청 자격 및 지원 금액 안내",           "국토교통부",         "복지·주거"),
        ("신생아 특례 구입·전세자금대출 신청 안내",        "국토교통부",         "주거·출산"),
        # 출산·육아
        ("출산지원금 바우처 및 영아수당 신청 방법 정리",   "보건복지부",         "출산·육아"),
        ("육아휴직급여 신청 방법 및 지원 금액 안내",       "고용노동부",         "육아"),
        ("아이돌봄서비스 신청 방법 및 정부 지원 안내",     "여성가족부",         "육아"),
        # 농업·에너지·여성
        ("농업인 직불금 신청 방법 및 지원 금액 안내",      "농림축산식품부",     "농업"),
        ("태양광 설치 보조금 주택용 에너지 지원사업 안내", "산업통상자원부",     "에너지"),
        ("여성기업 지원사업 및 여성창업 교육 프로그램",    "중소벤처기업부",     "여성·창업"),
    ]

    idx = datetime.now().timetuple().tm_yday % len(topic_pool)
    title, agency, category = topic_pool[idx]
    print("   → 날짜 로테이션 선택 (인덱스 " + str(idx) + "/" + str(len(topic_pool)) + "): " + title)
    return [{
        "title": title, "summary": "", "link": "",
        "source": agency, "category": category,
        "period": "", "score": 3,
    }]


# ── 중복 제거 + 우선순위 점수화 ──────────────────────────

def _deduplicate_and_rank(items):
    """
    여러 소스에서 수집된 항목의 중복을 제거하고 점수 순으로 정렬합니다.
    """
    seen = set()
    unique = []
    for item in sorted(items, key=lambda x: x.get("score", 0), reverse=True):
        # 제목 앞 10글자로 중복 판별
        key = item["title"][:10].strip()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


# ── 카테고리 추정 ─────────────────────────────────────────

def _guess_category(title):
    mapping = [
        ("청년", "청년"), ("창업", "창업"), ("취업", "취업·고용"),
        ("고용", "취업·고용"), ("복지", "복지"), ("주거", "주거"),
        ("소상공인", "소상공인"), ("중소기업", "중소기업"),
        ("스마트", "기술·제조"), ("에너지", "환경·에너지"),
        ("여성", "여성"), ("장애", "복지·장애"), ("농업", "농업"),
        ("출산", "출산·육아"), ("육아", "육아"), ("노인", "노인"),
    ]
    for kw, cat in mapping:
        if kw in title:
            return cat
    return "일반지원"


# ── 메인 수집 함수 ────────────────────────────────────────

def fetch_rss_candidates(max_items=5):
    """
    멀티 소스 수집 — 우선순위 순으로 시도, 자동 폴백

    우선순위:
    1. RSS 피드       (실제 최신 공고, 성공 시 최고 품질)
    2. Gemini 웹검색  (Google Grounding으로 최신 정보)
    3. Gemini 지식    (학습 데이터 기반 추론)
    4. 날짜 로테이션  (항상 성공 보장)
    """
    all_items = []

    # ① RSS 시도 (실패 격리)
    print("   [소스 1/4] RSS 피드 수집 시도...")
    rss_items = _collect_via_rss(max_items)
    if rss_items:
        print("   ✅ RSS 성공: " + str(len(rss_items)) + "개")
        all_items.extend(rss_items)
    else:
        print("   ❌ RSS 실패 (GitHub Actions IP 차단) — 다음 소스로")

    # ② Gemini 웹 검색 (RSS 실패 또는 보완)
    if len(all_items) < max_items:
        print("   [소스 2/4] Gemini 웹 검색 Grounding 시도...")
        gs_items = _collect_via_gemini_search(max_items)
        if gs_items:
            print("   ✅ Gemini 웹검색 성공: " + str(len(gs_items)) + "개")
            all_items.extend(gs_items)
        else:
            print("   ❌ Gemini 웹검색 실패 — 다음 소스로")

    # ③ Gemini 지식 기반 (보완)
    if len(all_items) < max_items:
        print("   [소스 3/4] Gemini 지식 기반 추론 시도...")
        gk_items = _collect_via_gemini_knowledge(max_items)
        if gk_items:
            print("   ✅ Gemini 지식 기반 성공: " + str(len(gk_items)) + "개")
            all_items.extend(gk_items)
        else:
            print("   ❌ Gemini 지식 기반 실패 — 다음 소스로")

    # ④ 날짜 로테이션 (최후 보루 — 항상 성공)
    if not all_items:
        print("   [소스 4/4] 날짜 기반 주제 로테이션...")
        all_items.extend(_collect_via_rotation())

    # 중복 제거 + 점수 정렬
    final = _deduplicate_and_rank(all_items)
    print("\n   📋 최종 수집 결과: " + str(len(final)) + "개 (중복 제거 후)")
    for i, item in enumerate(final[:max_items], 1):
        print("   " + str(i) + ". [" + item["source"] + "] " + item["title"])

    return final[:max_items]


def fetch_article_text(url, max_chars=3000):
    """공고 원문 수집 (접근 가능한 경우에만)"""
    if not url:
        return ""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception as e:
        print("   원문 수집 오류: " + str(e)[:50])
        return ""
