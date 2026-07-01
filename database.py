"""
Datenbankmodelle: speichert Kontakte und den Gesprächsverlauf
über alle Kanäle hinweg (E-Mail, Anruf, WhatsApp, Chat).
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from config import settings

Base = declarative_base()


class Contact(Base):
    """Ein Kontakt = eine Person, identifiziert über E-Mail oder Telefonnummer."""
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True)
    identifier = Column(String, unique=True, index=True)  # z.B. E-Mail-Adresse oder Telefonnummer
    name = Column(String, nullable=True)
    channel = Column(String)  # "email" | "call" | "whatsapp" | "chat"
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("Message", back_populates="contact")


class Message(Base):
    """Eine einzelne Nachricht im Verlauf (eingehend oder von der KI gesendet)."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    channel = Column(String)
    direction = Column(String)  # "incoming" | "outgoing"
    content = Column(Text)
    escalated = Column(Integer, default=0)  # 1 = an Mensch weitergeleitet statt automatisch beantwortet
    created_at = Column(DateTime, default=datetime.utcnow)

    contact = relationship("Contact", back_populates="messages")


engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)


def get_or_create_contact(session, identifier: str, channel: str, name: str = None) -> Contact:
    contact = session.query(Contact).filter_by(identifier=identifier).first()
    if not contact:
        contact = Contact(identifier=identifier, channel=channel, name=name)
        session.add(contact)
        session.commit()
        session.refresh(contact)
    return contact


def get_recent_history(session, contact_id: int, limit: int = 10):
    return (
        session.query(Message)
        .filter_by(contact_id=contact_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()[::-1]
    )


def save_message(session, contact_id: int, channel: str, direction: str, content: str, escalated: bool = False):
    msg = Message(
        contact_id=contact_id,
        channel=channel,
        direction=direction,
        content=content,
        escalated=1 if escalated else 0,
    )
    session.add(msg)
    session.commit()
    return msg
