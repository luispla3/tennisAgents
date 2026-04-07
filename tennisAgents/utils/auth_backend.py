from pathlib import Path

import firebase_admin
from fastapi import Header, HTTPException
from firebase_admin import auth as fb_auth
from firebase_admin import credentials


_SERVICE_ACCOUNT_PATH = (
    # Subimos dos niveles desde tennisAgents/utils/ hasta la raíz del repo
    Path(__file__).resolve().parents[2]
    / "tennisagents-firebase-adminsdk-fbsvc-9934dce4de.json"
)

if not firebase_admin._apps:
    cred = credentials.Certificate(str(_SERVICE_ACCOUNT_PATH))
    firebase_admin.initialize_app(cred)


async def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        print("[AUTH ERROR] Missing or invalid Authorization header:", authorization)
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )

    token = authorization.split(" ", 1)[1]
    try:
        decoded = fb_auth.verify_id_token(token)
    except Exception as e:
        print(f"[AUTH ERROR] Invalid or expired token: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {str(e)}")

    return decoded

