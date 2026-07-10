"""
분석 모듈 — 공고 원문 구조화 + FAQ 생성 + 관련 지원사업 추천
"""
import json
import re
from gemini_client import call_gemini


# ── 공고 정보 구조화 ──────────────────────────────────────

def extract_support_info(topic, article_text=""):
    """
    RSS 제목/요약 + 원문을 바탕으로 지원사업 핵심 정보를 JSON으로 추출합니다.

    반환 예시:
    {
      "title": "소상공인 경영안정자금",
      "agency": "중소벤처기업부",
      "target": "소상공인",
      "benefit": "최대 2,000만 원 융자",
      "period": "2025.03.01 ~ 예산 소진 시",
      "how_to_apply": "중소벤처기업부 누리집 온라인 신청",
      "documents": ["사업자등록증", "최근 3개월 매출 내역"],
      "precautions": ["중복 신청 불가", "만기 후 상환 의무"],
      "official_url": "https://www.mss.go.kr",
      "contact": "중소기업통합콜센터 1357"
    }
    """
    context = "제목: " + topic["title"] + "\n출처: " + topic["source"]
    if topic.get("summary"):
        context += "\n요약: " + topic["summary"]
    if article_text:
        context += "\n\n공고 원문 (일부):\n" + article_text

    json_template = (
        '{"title":"사업명","agency":"주관기관","target":"지원대상",'
        '"benefit":"지원내용 및 금액","period":"신청기간",'
        '"how_to_apply":"신청방법","documents":["서류1","서류2"],'
        '"precautions":["주의사항1","주의사항2"],'
        '"official_url":"공식URL","contact":"문의처"}'
    )

    prompt = "\n".join([
        "당신은 대한민국 정부 지원사업 전문 분석가입니다.",
        "아래 공고 정보를 분석해 JSON으로 정리해주세요.",
        "",
        context,
        "",
        "규칙:",
        "- 정보가 없는 항목은 '확인 필요'로 작성",
        "- 반드시 아래 JSON 형식만 출력 (코드펜스 없이)",
        "",
        json_template,
    ])

    for attempt in range(1, 4):
        try:
            raw = call_gemini(prompt, max_tokens=2048, temperature=0.3)
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"\s*```\s*$", "", raw, flags=re.MULTILINE)
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                raise ValueError("JSON 블록 없음")
            result = json.loads(m.group())
            print("   → 공고 정보 구조화 완료 (시도 " + str(attempt) + "회)")
            return result
        except (json.JSONDecodeError, ValueError) as e:
            print("   ⚠️  구조화 시도 " + str(attempt) + "/3 실패: " + str(e))

    # 실패 시 기본값
    return {
        "title": topic["title"], "agency": topic["source"],
        "target": "확인 필요", "benefit": "확인 필요",
        "period": "확인 필요", "how_to_apply": "공식 사이트 확인",
        "documents": [], "precautions": [],
        "official_url": topic.get("link", ""), "contact": "확인 필요",
    }


# ── FAQ 생성 ──────────────────────────────────────────────

def generate_faq(support_info):
    """
    지원사업 정보를 바탕으로 실제 신청자들이 궁금해하는 FAQ 5개를 생성합니다.
    반환: [{"q": "질문", "a": "답변"}, ...]
    """
    prompt = "\n".join([
        "당신은 정부 지원사업 상담 전문가입니다.",
        "",
        "다음 지원사업에 대해 실제 신청자들이 가장 많이 묻는 질문 5개와 답변을 작성해주세요.",
        "",
        "사업명: " + support_info.get("title", ""),
        "지원대상: " + support_info.get("target", ""),
        "지원내용: " + support_info.get("benefit", ""),
        "신청방법: " + support_info.get("how_to_apply", ""),
        "",
        "규칙:",
        "- 실용적이고 구체적인 질문 중심",
        "- 반드시 아래 JSON 배열 형식만 출력 (코드펜스 없이)",
        "",
        '[{"q":"질문1","a":"답변1"},{"q":"질문2","a":"답변2"}]',
    ])

    for attempt in range(1, 3):
        try:
            raw = call_gemini(prompt, max_tokens=2048, temperature=0.5)
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"\s*```\s*$", "", raw, flags=re.MULTILINE)
            m = re.search(r"\[.*\]", raw, re.DOTALL)
            if not m:
                raise ValueError("JSON 배열 없음")
            result = json.loads(m.group())
            print("   → FAQ " + str(len(result)) + "개 생성 완료")
            return result
        except (json.JSONDecodeError, ValueError) as e:
            print("   ⚠️  FAQ 생성 시도 " + str(attempt) + "/2 실패: " + str(e))

    return [{"q": "신청 방법이 궁금합니다.", "a": "공식 사이트에서 확인하시기 바랍니다."}]


# ── 관련 지원사업 추천 ────────────────────────────────────

def find_related_programs(support_info):
    """
    현재 지원사업과 함께 신청하면 좋은 관련 지원사업 3개를 추천합니다.
    반환: [{"name": "사업명", "agency": "기관", "summary": "한줄요약"}, ...]
    """
    prompt = "\n".join([
        "당신은 정부 지원사업 전문가입니다.",
        "",
        "아래 지원사업을 신청하는 사람에게 함께 활용하면 좋은 다른 정부 지원사업 3개를 추천해주세요.",
        "",
        "대상 사업: " + support_info.get("title", ""),
        "카테고리: " + support_info.get("target", ""),
        "",
        "규칙:",
        "- 실제 존재하는 정부 지원사업만 추천",
        "- 반드시 아래 JSON 배열 형식만 출력 (코드펜스 없이)",
        "",
        '[{"name":"사업명","agency":"주관기관","summary":"한줄요약"}]',
    ])

    for attempt in range(1, 3):
        try:
            raw = call_gemini(prompt, max_tokens=1024, temperature=0.5)
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"\s*```\s*$", "", raw, flags=re.MULTILINE)
            m = re.search(r"\[.*\]", raw, re.DOTALL)
            if not m:
                raise ValueError("JSON 배열 없음")
            result = json.loads(m.group())
            print("   → 관련 지원사업 " + str(len(result)) + "개 추천 완료")
            return result
        except (json.JSONDecodeError, ValueError) as e:
            print("   ⚠️  관련사업 추천 시도 " + str(attempt) + "/2 실패: " + str(e))

    return []


# ── 정책 배경 생성 ────────────────────────────────────────

def generate_policy_background(support_info):
    """
    해당 지원사업이 왜 생겼는지 정책 배경과 목적을 2~3문장으로 생성합니다.
    """
    prompt = "\n".join([
        "정부 지원사업 전문가로서, 아래 사업이 왜 만들어졌는지",
        "정책 배경과 목적을 2~3문장으로 자연스러운 한국어로 설명해주세요.",
        "독자는 일반 국민입니다. 부드럽고 이해하기 쉽게 작성하세요.",
        "",
        "사업명: " + support_info.get("title", ""),
        "주관: " + support_info.get("agency", ""),
        "지원대상: " + support_info.get("target", ""),
        "",
        "정책 배경 (2~3문장만 출력):",
    ])

    try:
        result = call_gemini(prompt, max_tokens=512, temperature=0.6)
        print("   → 정책 배경 생성 완료")
        return result
    except Exception as e:
        print("   ⚠️  정책 배경 생성 실패: " + str(e))
        return ""
