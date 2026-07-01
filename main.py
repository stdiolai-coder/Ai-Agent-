"""
Startpunkt der Anwendung. Bindet alle Kanal-Handler in eine FastAPI-App
ein und startet beim Hochfahren die Datenbank sowie die E-Mail-Abfrage
als Hintergrund-Task.

Starten mit:
    uvicorn main:app --reload

Webhooks, die du bei Twilio hinterlegen musst (nach Deployment):
    Anrufe eingehend:  https://DEINE-DOMAIN/voice/incoming
    Anruf verpasst:    https://DEINE-DOMAIN/voice/missed
    WhatsApp:          https://DEINE-DOMAIN/whatsapp/incoming

Web-Chat-Widget verbindet sich per WebSocket mit:
    wss://DEINE-DOMAIN/chat/ws
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

import database as db
import email_handler
from call_handler import router as call_router
from whatsapp_handler import router as whatsapp_router
from chat_handler import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Beim Start ---
    db.init_db()
    email_task = asyncio.create_task(email_handler.email_polling_loop())
    print("KI-Agent gestartet. E-Mail-Überwachung läuft im Hintergrund.")

    yield

    # --- Beim Herunterfahren ---
    email_task.cancel()


app = FastAPI(
    title="KI-Agent für Unternehmen",
    description="Beantwortet automatisch E-Mails, Anrufe, WhatsApp und Web-Chat.",
    lifespan=lifespan,
)

app.include_router(call_router)
app.include_router(whatsapp_router)
app.include_router(chat_router)


@app.get("/")
async def health_check():
    return {"status": "running", "message": "KI-Agent läuft."}
