"""
Das "Gehirn" des Agenten. Nimmt eine eingehende Nachricht plus Verlauf,
entscheidet ob eskaliert werden muss, und generiert sonst eine Antwort
über die Claude API.

Dieses Modul ist kanal-unabhängig: E-Mail, Anruf, WhatsApp und Chat
rufen alle dieselbe Funktion `generate_reply()` auf.
"""
import anthropic

from config import settings


SYSTEM_PROMPT_TEMPLATE = """Du bist der automatische Kundenservice-Assistent von "{company_name}".

Über das Unternehmen: {company_description}

Deine Aufgabe:
- Beantworte Anfragen von Kunden freundlich, klar und professionell auf Deutsch.
- Halte Antworten kurz und konkret.
- Wenn du eine Information nicht sicher weißt (z.B. genaue Preise, Verfügbarkeiten,
  interne Abläufe), erfinde NICHTS. Sag stattdessen, dass sich ein Mitarbeiter
  zeitnah meldet.
- Du antwortest vollautomatisch ohne menschliche Prüfung. Sei deshalb bei
  Zusagen (Rabatte, Termine, Garantien) zurückhaltend.
- Passe deinen Ton dem Kanal an: E-Mails etwas formeller, Chat/WhatsApp lockerer.
"""


class EscalationRequired(Exception):
    """Wird ausgelöst, wenn das Thema nicht automatisch beantwortet werden soll."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def needs_escalation(message: str) -> str | None:
    """Prüft, ob die Nachricht ein Eskalations-Schlüsselwort enthält.
    Gibt das gefundene Stichwort zurück, oder None."""
    lowered = message.lower()
    for keyword in settings.ESCALATION_KEYWORDS:
        if keyword in lowered:
            return keyword
    return None


def _build_messages(history: list, new_message: str) -> list:
    """Baut die Nachrichtenliste im Anthropic-API-Format aus dem Verlauf."""
    messages = []
    for msg in history:
        role = "user" if msg.direction == "incoming" else "assistant"
        messages.append({"role": role, "content": msg.content})
    messages.append({"role": "user", "content": new_message})
    return messages


def generate_reply(channel: str, new_message: str, history: list) -> dict:
    """
    Generiert eine Antwort auf eine eingehende Nachricht.

    Args:
        channel: "email" | "call" | "whatsapp" | "chat"
        new_message: der Text der eingehenden Nachricht (bei Anrufen: Transkript)
        history: Liste vorheriger Message-Objekte (aus der Datenbank) für Kontext

    Returns:
        dict mit:
          - "escalate": bool, True wenn an Mensch weitergeleitet werden soll
          - "reason": Grund für Eskalation (falls escalate=True)
          - "reply": generierter Antworttext (falls escalate=False)
    """
    keyword = needs_escalation(new_message)
    if keyword:
        return {
            "escalate": True,
            "reason": f"Schlüsselwort erkannt: '{keyword}'",
            "reply": None,
        }

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        company_name=settings.COMPANY_NAME,
        company_description=settings.COMPANY_DESCRIPTION,
    ) + f"\n\nAktueller Kanal: {channel}"

    messages = _build_messages(history, new_message)

    response = client.messages.create(
        model=settings.AI_MODEL,
        max_tokens=600,
        system=system_prompt,
        messages=messages,
    )

    reply_text = "".join(
        block.text for block in response.content if block.type == "text"
    )

    return {"escalate": False, "reason": None, "reply": reply_text}
