"""
작성 모듈 — 고품질 블로그 원고 생성
구조화된 JSON 데이터를 바탕으로 고정 템플릿으로 작성합니다.
"""
import json
import re
from gemini_client import call_gemini
from config import BLOG_SECTIONS


def build_meta(support_info, faq, related, background):
    """
    수집된 모든 정보를 바탕으로 블로그 메타데이터를 생성합니다.
    (제목, 설명, 키워드, 이미지 쿼리)
    """
    summary = "\n".join([
        "사업명: " + support_info.get("title", ""),
        "기관: " + support_info.get("agency", ""),
        "대상: " + support_info.get("target", ""),
        "혜택: " + support_info.get("benefit", ""),
        "기간: " + support_info.get("period", ""),
    ])

    json_template = (
        '{"blog_title":"클릭을 유도하는 블로그 제목 (35자 이내)",'
        '"description":"포스팅 요약 80자 이내",'
        '"keywords":["키워드1","키워드2","키워드3","키워드4","키워드5"],'
        '"pexels_query":"영문 이미지 검색어 2단어"}'
    )

    prompt = "\n".join([
        "당신은 SEO 전문 블로그 에디터입니다.",
        "아래 정부 지원사업 정보를 바탕으로 블로그 메타데이터를 JSON으로 만들어주세요.",
        "",
        summary,
        "",
        "규칙:",
        "- blog_title: 클릭률 높은 제목 (혜택·숫자 포함 권장)",
        "- keywords: SEO 핵심 키워드 5개",
        "- pexels_query: 영문 2단어 (예: korea small business)",
        "- 코드펜스 없이 JSON만 출력",
        "",
        json_template,
    ])

    for attempt in range(1, 4):
        try:
            raw = call_gemini(prompt, max_tokens=1024, temperature=0.7)
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"\s*```\s*$", "", raw, flags=re.MULTILINE)
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                raise ValueError("JSON 없음")
            meta = json.loads(m.group())
            print("   → 메타데이터 생성 완료 (시도 " + str(attempt) + "회)")
            return meta
        except (json.JSONDecodeError, ValueError) as e:
            print("   ⚠️  메타 시도 " + str(attempt) + "/3 실패: " + str(e))

    return {
        "blog_title": support_info.get("title", "정부 지원사업 안내"),
        "description": support_info.get("benefit", ""),
        "keywords": ["정부지원", "지원사업", "신청방법"],
        "pexels_query": "korea government support",
    }


def write_post(support_info, faq, related, background, meta):
    """
    구조화된 모든 정보를 바탕으로 고정 9단계 템플릿 마크다운 본문을 작성합니다.
    """
    # FAQ 텍스트 변환
    faq_text = ""
    for i, item in enumerate(faq, 1):
        faq_text += "Q" + str(i) + ". " + item.get("q", "") + "\n"
        faq_text += "A. " + item.get("a", "") + "\n\n"

    # 관련 사업 텍스트 변환
    related_text = ""
    for item in related:
        related_text += "- **" + item.get("name", "") + "** (" + item.get("agency", "") + "): " + item.get("summary", "") + "\n"

    # 서류 목록
    docs_text = "\n".join(["- " + d for d in support_info.get("documents", [])]) or "- 공식 사이트에서 확인"
    # 주의사항
    precautions_text = "\n".join(["- " + p for p in support_info.get("precautions", [])]) or "- 공식 공고문 참조"

    prompt = "\n".join([
        "당신은 대한민국 정부 지원사업 전문 블로그 작가입니다.",
        "아래 구조화된 정보를 바탕으로 블로그 본문을 작성해주세요.",
        "",
        "═══ 지원사업 정보 ═══",
        "사업명: " + support_info.get("title", ""),
        "주관기관: " + support_info.get("agency", ""),
        "지원대상: " + support_info.get("target", ""),
        "지원내용: " + support_info.get("benefit", ""),
        "신청기간: " + support_info.get("period", ""),
        "신청방법: " + support_info.get("how_to_apply", ""),
        "제출서류:",
        docs_text,
        "주의사항:",
        precautions_text,
        "공식URL: " + support_info.get("official_url", ""),
        "문의처: " + support_info.get("contact", ""),
        "",
        "═══ 정책 배경 ═══",
        background or "(정책 배경 정보 없음)",
        "",
        "═══ 자주 묻는 질문 ═══",
        faq_text or "(FAQ 없음)",
        "",
        "═══ 관련 지원사업 ═══",
        related_text or "(관련 사업 없음)",
        "",
        "═══ 작성 규칙 ═══",
        "1. 부드럽고 자연스러운 한국어 (공문체 절대 금지)",
        "2. 마크다운 형식 사용 (## 소제목, **볼드**, - 목록, > 인용)",
        "3. 전체 2,800자 ~ 3,200자 (공백 포함)",
        "4. 독자가 바로 신청할 수 있도록 실용적 정보 중심",
        "5. 공식 정보 외 추측 내용 금지",
        "",
        "═══ 반드시 아래 9개 섹션 순서대로 작성 ═══",
        "## 1. 지원사업 소개 및 배경",
        "## 2. 지원 대상",
        "## 3. 지원 내용 및 혜택",
        "## 4. 신청 기간 및 방법",
        "## 5. 제출 서류",
        "## 6. 자주 묻는 질문 (FAQ)",
        "## 7. 신청 시 주의사항",
        "## 8. 함께 보면 좋은 지원사업",
        "## 9. 공식 사이트 및 문의처",
        "",
        "코드펜스나 JSON 없이 마크다운 텍스트만 출력하세요.",
        "지금 바로 본문을 작성하세요:",
    ])

    for attempt in range(1, 4):
        try:
            raw = call_gemini(prompt, max_tokens=8192, temperature=0.7)
            raw = re.sub(r"^```(?:markdown)?\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"\s*```\s*$", "", raw, flags=re.MULTILINE)
            raw = raw.strip()
            if len(raw) < 1000:
                raise ValueError("본문 너무 짧음 (" + str(len(raw)) + "자)")
            print("   → 본문 생성 완료 (" + str(len(raw)) + "자, 시도 " + str(attempt) + "회)")
            return raw
        except ValueError as e:
            print("   ⚠️  본문 시도 " + str(attempt) + "/3 실패: " + str(e))

    raise RuntimeError("본문 생성 3회 모두 실패")
