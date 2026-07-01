"""
WhatsApp-Kanal über die Twilio WhatsApp Business API.

Setup: In der Twilio-Console die WhatsApp-Sandbox (oder eine genehmigte
WhatsApp-Business-Nummer) so konfigurieren, dass eingehende Nachrichten
an https://DEINE-DOMAIN/whatsapp/incoming gesendet werden.
"""
from fastapi import APIRouter, Form
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse

from config import settings
import database as db
import ai_brain

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.post("/incoming")
async def incoming_whatsapp(
    From: str = Form(...),
    Body: str = Form(default=""),
):
    """Empfängt eine WhatsApp-Nachricht und antwortet automatisch per KI."""
    session = db.SessionLocal()
    twiml_response = MessagingResponse()
    try:
        contact = db.get_or_create_contact(session, identifier=From, channel="whatsapp")
        history = db.get_recent_history(session, contact.id)
        db.save_message(session, contact.id, "whatsapp", "incoming", Body)

        result = ai_brain.generate_reply("whatsapp", Body, history)

        if result["escalate"]:
            text = (
                "Danke für Ihre Nachricht! Ein Mitarbeiter meldet sich persönlich "
                "bei Ihnen, da es um ein Thema geht, das wir nicht automatisch "
                "beantworten."
            )
            db.save_message(session, contact.id, "whatsapp", "incoming", Body, escalated=True)
            # TODO: Team-Benachrichtigung einbauen (Slack/E-Mail)
        else:
            text = result["reply"]
            db.save_message(session, contact.id, "whatsapp", "outgoing", text)

        twiml_response.message(text)
        return Response(content=str(twiml_response), media_type="application/xml")
    finally:
        session.close()
