
from fastapi import FastAPI, Query
import requests
import os
import json
from datetime import datetime

app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware
from scenario_engine import validate_surface_scenario, rescore_entries

ALLOWED_ORIGINS = [
    item.strip()
    for item in os.getenv(
        "BETIGO_ALLOWED_ORIGINS",
        "https://kra-betigo-live.dubaissday.chatgpt.site,http://localhost:3000",
    ).split(",")
    if item.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "kra-betigo-api", "contract": "KRA_BETIGO_HEALTH_V1"}

@app.post("/kra/scenario")
def scenario(payload: dict):
    """Fail-closed manual surface scenario endpoint.

    A release is returned only when every runner carries at least three
    past-only surface observations and a precomputed base_score. The current
    entry API does not invent those fields, so missing evidence remains HOLD.
    """
    try:
        validated = validate_surface_scenario(
            payload.get("track_condition"),
            payload.get("moisture_percent"),
            payload.get("pace_pressure", "MODEL_AUTO"),
        )
    except ValueError as exc:
        return {
            "status": "INVALID",
            "rescored": False,
            "release_blocked": True,
            "reason_code": "INVALID_SURFACE_INPUT",
            "message": str(exc),
        }
    entries = payload.get("entries") or []
    result = rescore_entries(entries, validated)
    result.update({
        "contract": "KRA_SURFACE_SCENARIO_V1",
        "requested_scenario": {
            "track_condition": validated.track_condition,
            "moisture_percent": validated.moisture_percent,
            "moisture_band": validated.moisture_band,
            "pace_pressure": validated.pace_pressure,
        },
        "target_result_used": False,
        "prediction_frozen_before_result": True,
        "publication_status": "RELEASED" if result["status"] == "READY" else "HOLD",
    })
    return result


KRA_API_KEY = os.getenv("KRA_API_KEY")

@app.get("/kra/entry")
def get_entry(rc_date: str = Query(...), rc_no: int = Query(...), meet: int = Query(...)):
    url = "https://apis.data.go.kr/B551015/API26_2"
    params = {
        "ServiceKey": KRA_API_KEY,
        "rc_date": rc_date,
        "rc_no": rc_no,
        "meet": meet,
        "_type": "json"
    }

    print(f"📡 /kra/entry 호출됨 → rc_date={rc_date}, rc_no={rc_no}, meet={meet}")
    try:
        response = requests.get(url, params=params, timeout=10, verify=False)
        print("🧾 응답 상태 코드:", response.status_code)
        data = response.json()
        print("📦 응답 본문:", data)

        items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
        if not isinstance(items, list):
            items = [items]

        parsed = []
        for item in items:
            try:
                horse = {
                    "마번": int(item.get("hrNo", 0)),
                    "마명": item.get("hrName", "-"),
                    "기수": item.get("jkName", "-"),
                    "조교사": item.get("trName", "-"),
                    "중량": float(item.get("wght", 0)),
                    "성장세": None,
                    "조교강도": None,
                    "전개유형": None,
                    "전개충돌": None
                }
                parsed.append(horse)
            except Exception as parse_error:
                print("⚠️ 개별 항목 파싱 실패:", parse_error)

        return {"status": "success", "entry_summary": parsed}

    except Exception as e:
        print("❌ API 요청 실패:", str(e))
        return {"status": "error", "message": str(e)}
