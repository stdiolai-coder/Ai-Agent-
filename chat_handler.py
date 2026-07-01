"""
Web-Chat-Kanal: einfaches WebSocket-Widget, das auf der eigenen Webseite
eingebunden werden kann.

Jede Browser-Sitzung bekommt eine zufällige Session-ID als "Identifier"
für die Kontakt-Historie (kein Login nötig für den Prototyp).
"""
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import settings
import database as db
import ai_brain

router = APIRouter(prefix="/chat", tags=["chat"])


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket):
    await websocket.accept()
    session_id = f"chat-{uuid.uuid4()}"
    db_session = db.SessionLocal()

    try:
        contact = db.get_or_create_contact(db_session, identifier=session_id, channel="chat")
        await websocket.send_json({
            "sender": "agent",
            "text": f"Hallo! Wie kann ich Ihnen bei {settings.COMPANY_NAME} helfen?",
        })

        while True:
            data = await websocket.receive_json()
            user_text = data.get("text", "")

            history = db.get_recent_history(db_session, contact.id)
            db.save_message(db_session, contact.id, "chat", "incoming", user_text)

            result = ai_brain.generate_reply("chat", user_text, history)

            if result["escalate"]:
                reply = (
                    "Danke! Das gebe ich an einen Mitarbeiter weiter, "
                    "der sich zeitnah meldet."
                )
                db.save_message(db_session, contact.id, "chat", "incoming", user_text, escalated=True)
            else:
                reply = result["reply"]
                db.save_message(db_session, contact.id, "chat", "outgoing", reply)

            await websocket.send_json({"sender": "agent", "text": reply})

    except WebSocketDisconnect:
        pass
    finally:
        db_session.close()
