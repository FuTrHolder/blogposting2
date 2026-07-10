"""
Gemini API 클라이언트 — 재시도 + 오류 처리 포함
"""
import time
import requests
from config import GEMINI_API_KEY, GEMINI_URL


def call_gemini(prompt, max_tokens=8192, temperature=0.7):
    """
    Gemini API 호출. 429/503 발생 시 지수 백오프 재시도.

    재시도 대기: 30s → 60s → 120s (최대 3회)
    텍스트가 있으면 MAX_TOKENS 종료도 허용.
    """
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature":     temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    wait_times = [30, 60, 120]

    for attempt in range(4):
        try:
            resp = requests.post(
                GEMINI_URL,
                params={"key": GEMINI_API_KEY},
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=120,
            )

            # 429 / 503 → 재시도
            if resp.status_code in (429, 503):
                if attempt < len(wait_times):
                    wait = wait_times[attempt]
                    print("   ⏳ Gemini " + str(resp.status_code) + " — " + str(wait) + "초 대기 후 재시도 ("
                          + str(attempt + 1) + "/3)...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()

            resp.raise_for_status()

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                feedback = data.get("promptFeedback", {})
                raise ValueError("Gemini candidates 없음: " + str(feedback))

            finish_reason = candidates[0].get("finishReason", "STOP")
            parts = candidates[0].get("content", {}).get("parts", [])

            if not parts or not parts[0].get("text", "").strip():
                raise ValueError("Gemini 텍스트 없음 (finishReason=" + finish_reason + ")")

            text = parts[0]["text"].strip()
            if finish_reason == "MAX_TOKENS":
                print("   ⚠️  MAX_TOKENS 종료 — 출력 텍스트 그대로 사용 (" + str(len(text)) + "자)")
            return text

        except requests.exceptions.HTTPError:
            raise
        except ValueError:
            raise

    raise RuntimeError("Gemini 호출 재시도 모두 실패")
