from fastapi import FastAPI, Query
import requests
import os

app = FastAPI()

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
        response = requests.get(url, params=params, timeout=10)
        print("🧾 응답 상태 코드:", response.status_code)
        data = response.json()
        print("📦 응답 본문:", data)

        items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
        if not isinstance(items, list):
            items = [items]

        parsed = []
        for item in items:
            parsed.append({
                "마번": int(item.get("hrNo", 0)),
                "마명": item.get("hrName"),
                "기수": item.get("jkName"),
                "조교사": item.get("trName"),
                "중량": float(item.get("wght", 0)),
                "성장세": None,
                "조교강도": None,
                "전개유형": None,
                "전개충돌": None
            })

        return {"status": "success", "entry_summary": parsed}

    except Exception as e:
        print("❌ API 요청 실패:", str(e))
        return {"status": "error", "message": str(e)}


@app.get("/kra/result")
def get_result(rc_date: str = Query(...), rc_no: int = Query(...), meet: int = Query(...)):
    url = "https://apis.data.go.kr/B551015/API17_1"
    params = {
        "ServiceKey": KRA_API_KEY,
        "rc_date": rc_date,
        "rc_no": rc_no,
        "meet": meet,
        "_type": "json"
    }

    print(f"📡 /kra/result 호출됨 → rc_date={rc_date}, rc_no={rc_no}, meet={meet}")

    try:
        response = requests.get(url, params=params, timeout=10)
        print("🧾 응답 상태 코드:", response.status_code)
        data = response.json()
        print("📦 응답 본문:", data)

        items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
        if not isinstance(items, list):
            items = [items]

        parsed = []
        for item in items:
            parsed.append({
                "착순": int(item.get("ord", 0)),
                "마번": int(item.get("hrNo", 0)),
                "마명": item.get("hrName"),
                "기수": item.get("jkName"),
                "도착차": item.get("rcDist"),
                "단승": item.get("winOdds"),
                "복승": item.get("qnlOdds")
            })

        parsed.sort(key=lambda x: x["착순"])
        return {"status": "success", "result_summary": parsed}

    except Exception as e:
        print("❌ API 요청 실패:", str(e))
        return {"status": "error", "message": str(e)}