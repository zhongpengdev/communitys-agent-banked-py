import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.api.session import router as session_router
from app.api.dialog import router as dialog_router
from app.api.tools import router as tools_router
from app.api.message import router as message_router

load_dotenv()

app = FastAPI(title="Community Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session_router)
app.include_router(dialog_router)
app.include_router(tools_router)
app.include_router(message_router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8081"))
    uvicorn.run(app, host="0.0.0.0", port=port)
