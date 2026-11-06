"""Owner email alerts with durable intent and conservative handling of lost SMTP replies."""

import argparse
import hashlib
import json
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import format_datetime

from sqlalchemy import select

from tsu.config import Settings
from tsu.db import make_engine, make_sessions
from tsu.models import Alert, SystemSetting, utcnow


def readiness(settings):
    configured = all(
        (
            settings.smtp_host,
            settings.smtp_from,
            settings.smtp_user,
            settings.smtp_password.get_secret_value(),
            settings.alert_email_to,
        )
    )
    return {
        "enabled": settings.alert_email_enabled,
        "configured": bool(configured),
        "recipient": settings.alert_email_to,
        "ready": bool(configured and settings.alert_email_enabled),
    }


def message(settings, alert):
    output = EmailMessage()
    output["Subject"] = "TechnoInno Studio : une vérification est nécessaire"
    output["From"] = settings.smtp_from
    output["To"] = settings.alert_email_to
    output["Date"] = format_datetime(utcnow())
    output["Message-ID"] = f"<tsu-alert-{alert.id}@studio.technoinno.live>"
    # Never include provider errors, prompts, credentials or user-supplied message text.
    labels = {
        "notification_test": (
            "Message d’essai : la liaison d’alerte du studio est en cours de vérification."
        ),
        "cost_reconciliation": "Une dépense doit être rapprochée.",
        "budget_blocked": "Le budget disponible ne permet pas de poursuivre.",
        "cost_overrun": "La production est arrêtée après un dépassement de coût.",
        "awaiting_local_edit": "Une vidéo attend une correction au montage.",
        "awaiting_owner_review": "Une vidéo attend votre avis.",
    }
    output.set_content(
        "Bonjour,\n\n"
        + labels.get(alert.kind, "Une opération du studio nécessite votre attention.")
        + "\n\n"
        "Consultez les détails dans votre studio :\nhttps://studio.technoinno.live/admin\n\n"
        "Aucune nouvelle génération payante n’est lancée par cette notification.\n"
    )
    return output


def send(settings, output, *, ssl_context=None):
    context = ssl_context or ssl.create_default_context()
    if not context.check_hostname or context.verify_mode != ssl.CERT_REQUIRED:
        raise ValueError("Email delivery requires verified TLS")
    connection = None
    try:
        if settings.smtp_security == "ssl":
            connection = smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port, timeout=10, context=context
            )
        else:
            connection = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
            connection.starttls(context=context)
        connection.login(settings.smtp_user, settings.smtp_password.get_secret_value())
        refused = connection.send_message(output)
        if refused:
            raise RuntimeError("The owner recipient was not accepted")
        # SMTP acceptance is not evidence that the recipient's inbox received it.
    finally:
        if connection:
            connection.close()


def deliver(settings, engine, *, ssl_context=None, limit=10):
    if not readiness(settings)["ready"]:
        return {"accepted": 0, "uncertain": 0, "disabled_or_unconfigured": True}
    sessions = make_sessions(engine)
    with sessions() as db:
        pending = list(
            db.scalars(
                select(Alert).where(Alert.resolved.is_(False)).order_by(Alert.created_at, Alert.id)
            )
        )
    accepted = uncertain = 0
    destination = hashlib.sha256(settings.alert_email_to.encode()).hexdigest()
    for alert in pending:
        if accepted + uncertain >= limit:
            break
        key = "email-alert:" + alert.id
        with sessions.begin() as db:
            # A conflicting insert is rolled back before SMTP. No duplicate send.
            if db.get(SystemSetting, key):
                continue
            db.add(
                SystemSetting(
                    key=key,
                    value={
                        "stage": "attempting",
                        "recipient_sha256": destination,
                        "at": utcnow().isoformat(),
                    },
                )
            )
        try:
            send(settings, message(settings, alert), ssl_context=ssl_context)
        except Exception:
            stage = "uncertain"
            uncertain += 1
        else:
            stage = "smtp_accepted"
            accepted += 1
        with sessions.begin() as db:
            state = db.get(SystemSetting, key)
            state.value = {**state.value, "stage": stage}
    return {"accepted": accepted, "uncertain": uncertain, "disabled_or_unconfigured": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--send-authorized-pending-alerts", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    if not args.send_authorized_pending_alerts:
        print(json.dumps(readiness(settings)))
        return
    engine = make_engine(settings.database_url.get_secret_value())
    try:
        print(json.dumps(deliver(settings, engine)))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
