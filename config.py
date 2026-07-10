"""
설정 파일 — 환경변수 및 상수 관리
"""
import os

# ── API 키 ─────────────────────────────────────────────────
GEMINI_API_KEY  = os.environ["GEMINI_API_KEY"]
PEXELS_API_KEY  = os.environ["PEXELS_API_KEY"]
GMAIL_USER      = os.environ["GMAIL_USER"]
GMAIL_APP_PASS  = os.environ["GMAIL_APP_PASS"]
RECIPIENT_EMAIL = os.environ["RECIPIENT_EMAIL"]

# ── Gemini 모델 ────────────────────────────────────────────
# gemini-2.5-flash-lite : 2026년 현재 무료 티어 활성 모델
# 1.5/2.0-flash 는 2025~2026년 순차 퇴역(404/503 오류)
GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + GEMINI_MODEL
    + ":generateContent"
)

# ── RSS 피드 ───────────────────────────────────────────────
RSS_FEEDS = [
    # 중소벤처기업부
    "https://www.mss.go.kr/site/smba/ex/bbs/RssReader.do?bbsId=BBSMSTR_000000000179",
    # 고용노동부
    "https://www.moel.go.kr/rss/pressRelease.rss",
    # 창업진흥원
    "https://www.kised.or.kr/rss/news.do",
    # K-Startup
    "https://www.k-startup.go.kr/rss/board.do?menuNo=200020",
    # 중소기업진흥공단
    "https://www.sbc.or.kr/rss/SBC_NEWS.xml",
]

# ── 폴백 주제 ──────────────────────────────────────────────
FALLBACK_TOPICS = [
    {"title": "2025 소상공인 경영안정자금 지원사업 신청 방법", "agency": "중소벤처기업부", "category": "창업·기업"},
    {"title": "청년 창업 지원금 자격 요건 및 신청 절차",       "agency": "중소벤처기업부", "category": "청년·창업"},
    {"title": "중소기업 스마트공장 구축 지원사업 안내",         "agency": "중소벤처기업부", "category": "기업·제조"},
    {"title": "여성기업 성장 지원 정책 총정리",                 "agency": "중소벤처기업부", "category": "여성·기업"},
    {"title": "국민취업지원제도 신청 방법 및 지원금 안내",       "agency": "고용노동부",     "category": "취업·고용"},
    {"title": "청년도약계좌 가입 조건 및 신청 절차",            "agency": "금융위원회",     "category": "청년·금융"},
    {"title": "신재생에너지 설치 보조금 신청 가이드",            "agency": "산업통상자원부", "category": "환경·에너지"},
    {"title": "중장년 재취업 지원 및 직업훈련 프로그램",         "agency": "고용노동부",     "category": "중장년·취업"},
    {"title": "주거급여 신청 자격 및 지원 금액 안내",           "agency": "국토교통부",     "category": "주거·복지"},
    {"title": "장애인 복지 지원사업 총정리",                    "agency": "보건복지부",     "category": "복지·장애"},
]

# ── 블로그 고정 템플릿 구조 ────────────────────────────────
BLOG_SECTIONS = [
    "지원사업 소개 및 배경",
    "지원 대상",
    "지원 내용 및 혜택",
    "신청 기간 및 방법",
    "제출 서류",
    "자주 묻는 질문 (FAQ)",
    "신청 시 주의사항",
    "함께 보면 좋은 지원사업",
    "공식 사이트 및 문의처",
]
