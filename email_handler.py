"""
E-Mail-Kanal: prüft per IMAP regelmäßig auf neue E-Mails, lässt die KI
antworten und sendet die Antwort per SMTP zurück.

Läuft als Hintergrund-Schleife (siehe 10_main.py, das diese Funktion
beim Start als Task einplant).
"""
import asyncio
import smtplib
import email
from email.message import EmailMessage
from imapclient import IMAPClient

from config import settings
import database as db
import ai_brain


def _send_reply(to_address: str, subject: str, body: str):
    msg = EmailMessage()
    msg["From"] = settings.EMAIL_ADDRESS
    msg["To"] = to_address
    msg["Subject"] = f"Re: {subject}" if not subject.lower().startswith("re:") else subject
    msg.set_content(body)

    with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)
        server.send_message(msg)


def _process_one_email(raw_message: bytes):
    parsed = email.message_from_bytes(raw_message)
    sender = email.utils.parseaddr(parsed.get("From"))[1]
    subject = parsed.get("Subject", "(kein Betreff)")

    body = ""
    if parsed.is_multipart():
        for part in parsed.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(errors="ignore")
                break
    else:
        body = parsed.get_payload(decode=True).decode(errors="ignore")

    session = db.SessionLocal()
    try:
        contact = db.get_or_create_contact(session, identifier=sender, channel="email")
        history = db.get_recent_history(session, contact.id)
        db.save_message(session, contact.id, "email", "incoming", body)

        result = ai_brain.generate_reply("email", body, history)

        if result["escalate"]:
            db.save_message(session, contact.id, "email", "incoming", body, escalated=True)
            print(f"[ESKALATION] E-Mail von {sender} braucht menschliche Antwort: {result['reason']}")
            # TODO: hier z.B. Benachrichtigung an Team senden (Slack, eigenes E-Mail-Postfach etc.)
            return

        _send_reply(sender, subject, result["reply"])
        db.save_message(session, contact.id, "email", "outgoing", result["reply"])
        print(f"[OK] Automatische Antwort an {sender} gesendet.")
    finally:
        session.close()


def check_inbox_once():
    """Prüft einmal auf neue, ungelesene E-Mails und beantwortet sie."""
    with IMAPClient(settings.IMAP_SERVER, port=settings.IMAP_PORT, ssl=True) as client:
        client.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)
        client.select_folder("INBOX")
        unseen_ids = client.search(["UNSEEN"])

        for uid in unseen_ids:
            raw = client.fetch([uid], ["RFC822"])[uid][b"RFC822"]
            try:
                _process_one_email(raw)
            except Exception as exc:
                print(f"[FEHLER] Konnte E-Mail {uid} nicht verarbeiten: {exc}")


async def email_polling_loop():
    """Hintergrund-Endlosschleife, die regelmäßig den Posteingang prüft."""
    while True:
        try:
            check_inbox_once()
        except Exception as exc:
            print(f"[FEHLER] E-Mail-Abruf fehlgeschlagen: {exc}")
        await asyncio.sleep(settings.EMAIL_POLL_INTERVAL_SECONDS)
