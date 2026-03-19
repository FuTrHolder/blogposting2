# 🇰🇷 대한민국 정부 지원사업 블로그 자동화 시스템 (완전 무료 버전)

> 💸 **총 운영 비용: ₩0/월** — 모든 구성요소가 무료 서비스로 동작합니다.

---

## 💰 비용 구조

| 구성 요소 | 서비스 | 무료 한도 | 실제 사용량 | 비용 |
|-----------|--------|-----------|------------|------|
| AI 글 생성 | Google Gemini 2.5 Flash | 250회/일 | 1회/일 | **₩0** |
| 이미지 검색 | Pexels API | 20,000회/월 | 1회/일 (약 30회/월) | **₩0** |
| 스케줄링 | GitHub Actions | 2,000분/월 | 약 5분/일 (150분/월) | **₩0** |
| 이메일 발송 | Gmail SMTP | 500건/일 | 1건/일 | **₩0** |
| **합계** | | | | **₩0/월** |

---

## 📁 파일 구조

```
blog-automation/
├── generate_post.py              # 메인 실행 파일 (수집 → 생성 → 발송)
├── send_email.py                 # Gmail 발송 모듈
├── requirements.txt              # Python 패키지 (feedparser, requests만 필요)
├── .github/
│   └── workflows/
│       └── daily_blog.yml        # GitHub Actions 스케줄러
└── output/                       # 생성된 마크다운 파일 저장 폴더
    └── post_YYYYMMDD.md
```

---

## ⚙️ 설정 방법 (Step by Step)

### Step 1. API 키 발급 (모두 무료)

#### 1-1. Google Gemini API 키 (AI 글 생성용)
1. https://aistudio.google.com 접속 (Google 계정으로 로그인)
2. 상단 **"Get API key"** 클릭 → **"Create API key"**
3. 키 복사 (형식: `AIzaSy...`)
4. ✅ 신용카드 불필요, 완전 무료

#### 1-2. Pexels API 키 (이미지 검색용)
1. https://www.pexels.com/join 에서 계정 생성
2. https://www.pexels.com/api 접속 → **"Get Started"** 클릭
3. 앱 이름/설명 입력 후 API 키 즉시 발급
4. ✅ 신용카드 불필요, 시간당 200회 / 월 20,000회 무료

#### 1-3. Gmail 앱 비밀번호 (이메일 발송용)
> ⚠️ 반드시 **2단계 인증**이 활성화된 Google 계정 필요

1. https://myaccount.google.com/apppasswords 접속
2. **앱 선택** → "메일", **기기 선택** → "기타 (직접 입력)"
3. 이름 입력 (예: "블로그자동화") → **생성**
4. 16자리 앱 비밀번호 복사 (공백 제거: `abcdefghijklmnop`)
5. ✅ 완전 무료

---

### Step 2. GitHub 저장소 생성 및 코드 업로드

```bash
git init
git add .
git commit -m "초기 설정: 무료 블로그 자동화 파이프라인"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/blog-automation.git
git push -u origin main
```

---

### Step 3. GitHub Secrets 등록 (기존 5개 → 5개, 내용 변경)

GitHub 저장소 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret 이름       | 값 예시                         | 발급처                            |
|------------------|---------------------------------|----------------------------------|
| `GEMINI_API_KEY` | `AIzaSyXXXXXXXXXXXXXXXXXXXXXX` | aistudio.google.com (무료)        |
| `PEXELS_API_KEY` | `563492ad6f91700001000001xxxx`  | pexels.com/api (무료)             |
| `GMAIL_USER`     | `yourname@gmail.com`            | Gmail 계정                        |
| `GMAIL_APP_PASS` | `abcdefghijklmnop`              | myaccount.google.com/apppasswords |
| `RECIPIENT_EMAIL`| `recipient@example.com`         | 수신할 이메일 주소                 |

> ℹ️ 기존 `ANTHROPIC_API_KEY`와 `UNSPLASH_ACCESS_KEY`는 더 이상 필요하지 않습니다.

---

### Step 4. 로컬 테스트

```bash
# 패키지 설치 (2개만 필요 — anthropic 패키지 불필요)
pip install -r requirements.txt

# 환경변수 설정 (macOS/Linux)
export GEMINI_API_KEY="AIzaSy..."
export PEXELS_API_KEY="563492..."
export GMAIL_USER="yourname@gmail.com"
export GMAIL_APP_PASS="abcdefghijklmnop"
export RECIPIENT_EMAIL="recipient@example.com"

# 실행
python generate_post.py
```

```powershell
# 환경변수 설정 (Windows PowerShell)
$env:GEMINI_API_KEY="AIzaSy..."
$env:PEXELS_API_KEY="563492..."
$env:GMAIL_USER="yourname@gmail.com"
$env:GMAIL_APP_PASS="abcdefghijklmnop"
$env:RECIPIENT_EMAIL="recipient@example.com"

python generate_post.py
```

---

### Step 5. GitHub Actions 수동 테스트

1. GitHub 저장소 → **Actions** 탭
2. **블로그 원고 자동 생성 및 발송 (완전 무료)** 클릭
3. **Run workflow** → **Run workflow** 클릭
4. 실행 로그 확인 + 이메일 수신 확인

---

## 📊 시스템 동작 흐름

```
매일 KST 07:00
      │
      ▼
[GitHub Actions 실행]  ← 무료 (월 2,000분 한도)
      │
      ▼
[1] RSS 피드 수집       ← 무료 (공공 RSS)
    ├─ 중소벤처기업부
    ├─ 고용노동부
    ├─ 창업진흥원
    └─ 중소기업진흥공단
      │
      ▼ (실패 시 → 자체 기획 주제 사용)
[2] Gemini 2.5 Flash   ← 무료 (일 250회 한도)
    포스팅 생성
    ├─ 3,000자 마크다운 작성
    └─ 이미지 쿼리 추출
      │
      ▼
[3] Pexels 이미지 검색  ← 무료 (월 20,000회 한도)
      │
      ▼
[4] 마크다운 파일 저장
      │
      ▼
[5] Gmail 이메일 발송   ← 무료 (일 500건 한도)
    ├─ HTML 본문 (미리보기)
    └─ .md 파일 첨부
      │
      ▼
[6] GitHub Artifact 저장 (30일 보관)
```

---

## 💡 자주 묻는 질문

**Q. Gemini API 무료 한도를 초과하면 어떻게 되나요?**
A. 하루 1회만 실행하므로 일 250회 한도에 걸릴 일이 없습니다. 만약 여러 번 테스트하다 한도를 소진하면, 다음날 자정(태평양 시간)에 자동으로 리셋됩니다.

**Q. Gemini 무료 티어에서 데이터가 학습에 사용되나요?**
A. Google 정책상 무료 티어에서는 입력 데이터가 모델 개선에 활용될 수 있습니다. 민감한 정보를 입력하지 않는 한 블로그 자동화 용도에는 문제없습니다. 걱정된다면 Google Cloud 유료 전환 시 데이터 학습 사용이 중단됩니다.

**Q. Pexels 이미지를 블로그에 사용해도 저작권 문제가 없나요?**
A. Pexels의 모든 사진은 상업적 이용 포함 무료로 사용 가능합니다. 단, 사진 작가 크레딧(출처 표기)을 포함하는 것이 권장됩니다. 코드에 크레딧 표기가 자동 포함되어 있습니다.

**Q. 발송 시간을 바꾸고 싶다면?**
A. `daily_blog.yml`의 cron 표현식을 수정하세요:
```yaml
- cron: "0 0 * * *"    # KST 09:00
- cron: "0 3 * * *"    # KST 12:00 (정오)
- cron: "0 22 * * 1-5" # 평일 KST 07:00만
```

---

## 🔄 기존 버전과 비용 비교

| 항목 | 기존 (유료) | 현재 (무료) | 절감액 |
|------|------------|------------|--------|
| AI 글 생성 | Claude API ~$0.05/일 | Gemini 무료 | ~$1.5/월 |
| 이미지 | Unsplash (시간당 50회 한도) | Pexels (월 20,000회) | ₩0, 한도 ↑ |
| 합계 | ~$1.5~3/월 | **₩0/월** | **100% 절감** |

---

*자동 생성 시스템 | Google Gemini API + Pexels + GitHub Actions + Gmail*
