"""python -m api  →  sobe a API e a interface em http://localhost:8000"""
import os

import uvicorn

uvicorn.run("api.main:app", host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")),
            reload=os.getenv("RELOAD", "0") == "1")
