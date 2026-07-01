"""
Das "Gehirn" des Agenten. Nimmt eine eingehende Nachricht plus Verlauf,
entscheidet ob eskaliert werden muss, und generiert sonst eine Antwort
über die Google Gemini API.
"""
import google.generativeai as genai

from config import settings


SYSTEM_PROMPT_TEMPLATE = """Du bist der automatische Kundenservice-Assistent von "{company_name}".

Über das Unternehmen: {company_description}

Deine Aufgabe:
- Beantworte Anfragen von Kunden freundlich, klar und professionell auf Deutsch.
- Halte Antworten kurz und konkret.
- Wenn du eine Information nicht sicher weißt, erfinde NICHTS. Sag stattdessen,
  dass sich ein Mitarbeiter zeitnah meldet.
- Du antwortest vollautomatisch ohne menschliche Prüfung. Sei deshalb bei
  Zusagen zurückhaltend.
- Passe deinen Ton dem Kanal an: E-Mails etwas formeller, Chat/WhatsApp lockerer.
"""


def needs_escalation(message: str) -> str | None:
    lowered = message.lower()
    for keyword in settings.ESCALATION_KEYWORDS:
        if keyword in lowered:
            return keyword
    return None


def _build_history(history: list) -> list:
    formatted = []
    for msg in history:
        role = "user" if msg.direction == "incoming" else "model"
        formatted.append({"role": role, "parts": [msg.content]})
    return formatted


def generate_reply(channel: str, new_message: str, history: list) -> dict:
    keyword = needs_escalation(new_message)
    if keyword:
        return {
            "escalate": True,
            "reason": f"Schlüsselwort erkannt: '{keyword}'",
            "reply": None,
        }

    genai.configure(api_key=settings.GOOGLE_API_KEY)

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        company_name=settings.COMPANY_NAME,
        company_description=settings.COMPANY_DESCRIPTION,
    ) + f"\n\nAktueller Kanal: {channel}"

    model = genai.GenerativeModel(
        model_name=settings.AI_MODEL,
        system_instruction=system_prompt,
    )

    chat = model.start_chat(history=_build_history(history))
    response = chat.send_message(new_message)

    return {"escalate": False, "reason": None, "reply": response.text}
