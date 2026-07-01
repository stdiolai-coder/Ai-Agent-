"""
Telefon-Kanal über Twilio.

Funktionsweise:
1. Ein Anruf kommt rein -> Twilio ruft unseren Webhook `/voice/incoming` auf.
2. Wir spielen eine Begrüßung ab und nehmen die Anfrage als Sprache auf
   (Twilio transkribiert automatisch zu Text).
3. Twilio ruft danach `/voice/process` mit dem Transkript auf.
4. Die KI generiert eine Antwort, die per Sprachausgabe (Text-to-Speech)
   vorgelesen wird.
5. Bei einem ECHTEN verpassten Anruf (niemand nimmt ab / Voicemail) greift
   `/voice/missed` und die KI schickt automatisch eine SMS mit Rückmeldung.

Hinweis: Erfordert eine Twilio-Telefonnummer, deren "A call comes in"-Webhook
auf https://DEINE-DOMAIN/voice/incoming zeigt.
"""
from fastapi import APIRouter, Form
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client as TwilioClient

from config import settings
import database as db
import ai_brain

router = APIRouter(prefix="/voice", tags=["voice"])

twilio_client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


@router.post("/incoming")
async def incoming_call():
    """Erster Kontaktpunkt bei eingehendem Anruf: Begrüßung + Frage aufnehmen."""
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action="/voice/process",
        language="de-DE",
        speech_timeout="auto",
    )
    gather.say(
        f"Willkommen bei {settings.COMPANY_NAME}. Wie kann ich Ihnen helfen?",
        language="de-DE",
    )
    response.append(gather)
    # Falls keine Spracheingabe erkannt wurde, nochmal versuchen
    response.redirect("/voice/incoming")
    return Response(content=str(response), media_type="application/xml")


@router.post("/process")
async def process_speech(
    From: str = Form(...),
    SpeechResult: str = Form(default=""),
):
    """Verarbeitet die Transkription der Spracheingabe und antwortet per KI."""
    session = db.SessionLocal()
    response = VoiceResponse()
    try:
        contact = db.get_or_create_contact(session, identifier=From, channel="call")
        history = db.get_recent_history(session, contact.id)
        db.save_message(session, contact.id, "call", "incoming", SpeechResult)

        if not SpeechResult.strip():
            response.say("Entschuldigung, ich habe Sie nicht verstanden.", language="de-DE")
            response.redirect("/voice/incoming")
            return Response(content=str(response), media_type="application/xml")

        result = ai_brain.generate_reply("call", SpeechResult, history)

        if result["escalate"]:
            response.say(
                "Vielen Dank. Ich verbinde Sie mit einem Mitarbeiter, "
                "bitte bleiben Sie in der Leitung.",
                language="de-DE",
            )
            # TODO: hier echte Weiterleitung an eine Mitarbeiter-Nummer einbauen, z.B.:
            # response.dial("+49XXXXXXXXX")
            db.save_message(session, contact.id, "call", "incoming", SpeechResult, escalated=True)
        else:
            response.say(result["reply"], language="de-DE")
            db.save_message(session, contact.id, "call", "outgoing", result["reply"])
            # Weiterer Dialog möglich
            gather = Gather(input="speech", action="/voice/process", language="de-DE", speech_timeout="auto")
            response.append(gather)

        return Response(content=str(response), media_type="application/xml")
    finally:
        session.close()


@router.post("/missed")
async def missed_call(From: str = Form(...)):
    """
    Wird aufgerufen, wenn ein Anruf nicht angenommen wurde (z.B. als
    Twilio-Fallback-Webhook konfiguriert). Schickt automatisch eine SMS.
    """
    session = db.SessionLocal()
    try:
        contact = db.get_or_create_contact(session, identifier=From, channel="call")
        history = db.get_recent_history(session, contact.id)

        prompt = "Ein Kunde hat gerade angerufen, aber es konnte niemand abnehmen."
        result = ai_brain.generate_reply("call", prompt, history)

        text = result["reply"] or (
            f"Hallo, hier ist {settings.COMPANY_NAME}. Entschuldigung, wir konnten "
            "gerade nicht abnehmen. Wir melden uns schnellstmöglich bei Ihnen zurück!"
        )

        twilio_client.messages.create(
            body=text,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=From,
        )
        db.save_message(session, contact.id, "call", "outgoing", f"[Auto-SMS] {text}")
        return {"status": "sms_sent"}
    finally:
        session.close()
