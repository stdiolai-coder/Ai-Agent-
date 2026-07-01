"""
Zentrale Konfiguration des KI-Agenten.
Lädt alle Zugangsdaten und Einstellungen aus der .env-Datei.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # --- Anthropic / KI ---
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    AI_MODEL: str = os.getenv("AI_MODEL", "claude-sonnet-5")

    # --- Unternehmens-Kontext (wird in den System-Prompt eingebaut) ---
    COMPANY_NAME: str = os.getenv("COMPANY_NAME", "Mein Unternehmen")
    COMPANY_DESCRIPTION: str = os.getenv(
        "COMPANY_DESCRIPTION", "Ein Unternehmen, das Kunden professionell betreut."
    )

    # --- E-Mail (IMAP/SMTP) ---
    EMAIL_ADDRESS: str = os.getenv("EMAIL_ADDRESS", "")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")
    IMAP_SERVER: str = os.getenv("IMAP_SERVER", "imap.gmail.com")
    IMAP_PORT: int = int(os.getenv("IMAP_PORT", "993"))
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    EMAIL_POLL_INTERVAL_SECONDS: int = int(os.getenv("EMAIL_POLL_INTERVAL_SECONDS", "30"))

    # --- Twilio (Anrufe & WhatsApp) ---
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    TWILIO_WHATSAPP_NUMBER: str = os.getenv("TWILIO_WHATSAPP_NUMBER", "")

    # --- Datenbank ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./agent.db")

    # --- Sicherheitsgrenzen für vollautomatische Antworten ---
    # Themen, bei denen die KI NICHT automatisch antworten, sondern eskalieren soll
    ESCALATION_KEYWORDS: list = [
        "beschwerde", "anwalt", "klage", "kündigung", "rechtlich",
        "rückerstattung", "erstattung", "stornierung",
    ]


settings = Settings()
