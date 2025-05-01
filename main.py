from fastapi import FastAPI, Query
import requests

app = FastAPI()

KRA_API_KEY = "YOUR_KRA_API_KEY"

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

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}