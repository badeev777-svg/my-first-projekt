from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import replicate
import os
import time
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

os.environ["REPLICATE_API_TOKEN"] = os.getenv("REPLICATE_API_TOKEN", "")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_last_request: dict[str, float] = defaultdict(float)
RATE_LIMIT_SECONDS = 10

MODEL = "cedoysch/flux-fill-redux-try-on:cf5cb07a25e726fe2fac166a8c5ab52ddccd48657741670fb09d9954d4d8446f"


class TryOnRequest(BaseModel):
    user_image: str
    cloth_image: str
    cloth_type: str = "upper"  # upper | lower | overall


# ----------------------------
# 1. TRY-ON
# ----------------------------
@app.post("/tryon")
def tryon(body: TryOnRequest, request: Request):
    client_ip = request.client.host
    elapsed = time.time() - _last_request[client_ip]
    if elapsed < RATE_LIMIT_SECONDS:
        raise HTTPException(status_code=429, detail=f"Wait {round(RATE_LIMIT_SECONDS - elapsed, 1)}s")

    _last_request[client_ip] = time.time()

    try:
        output = replicate.run(
            MODEL,
            input={
                "person_image": body.user_image,
                "cloth_image": body.cloth_image,
                "cloth_type": body.cloth_type,  # upper / lower / overall
            },
        )
        image_url = output[0] if isinstance(output, list) else str(output)
        return {"status": "done", "image": str(image_url)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {e}")


# ----------------------------
# 2. HEALTH CHECK
# ----------------------------
@app.get("/")
def health():
    return {"status": "ok"}
