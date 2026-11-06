"""Local SMTP-over-TLS exchange: acceptance, lost reply and disabled sending."""

import ipaddress
import socketserver
import ssl
import threading
from datetime import UTC, datetime, timedelta

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from pydantic import SecretStr
from sqlalchemy import select

from tsu.config import Settings
from tsu.db import make_sessions
from tsu.models import Alert, SystemSetting
from tsu.notifications import deliver


@pytest.fixture
def smtp(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    certfile, keyfile = tmp_path / "cert.pem", tmp_path / "key.pem"
    certfile.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    keyfile.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(certfile, keyfile)

    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.wfile.write(b"220 local synthetic SMTP\r\n")
            while line := self.rfile.readline():
                command = line.split(b" ")[0].strip().upper()
                if command in {b"EHLO", b"HELO"}:
                    self.wfile.write(b"250-localhost\r\n250 AUTH PLAIN\r\n")
                elif command == b"AUTH":
                    self.wfile.write(b"235 synthetic authenticated\r\n")
                elif command in {b"MAIL", b"RCPT", b"RSET"}:
                    self.wfile.write(b"250 OK\r\n")
                elif command == b"DATA":
                    self.wfile.write(b"354 send data\r\n")
                    content = []
                    while (part := self.rfile.readline()) not in {b".\r\n", b""}:
                        content.append(part)
                    self.server.messages.append(b"".join(content))
                    if self.server.lose_response:
                        return
                    self.wfile.write(b"250 accepted\r\n")
                else:
                    return

    class Server(socketserver.ThreadingTCPServer):
        daemon_threads = True

        def get_request(self):
            sock, address = super().get_request()
            return server_context.wrap_socket(sock, server_side=True), address

    server = Server(("127.0.0.1", 0), Handler)
    server.messages, server.lose_response = [], False
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    settings = Settings(
        _env_file=None,
        alert_email_enabled=True,
        alert_email_to="owner@example.invalid",
        smtp_host="127.0.0.1",
        smtp_port=server.server_address[1],
        smtp_security="ssl",
        smtp_user="synthetic",
        smtp_password="synthetic-password",
        smtp_from="studio@example.invalid",
    )
    context = ssl.create_default_context(cafile=str(certfile))
    yield server, settings, context
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


@pytest.mark.parametrize("lost", [False, True])
def test_smtp_tls_once_only_and_redacts_sensitive_error_details(local_engine, smtp, lost):
    server, settings, context = smtp
    server.lose_response = lost
    sessions = make_sessions(local_engine)
    with sessions.begin() as db:
        db.add(
            Alert(
                dedupe_key="problem",
                kind="owner_attention",
                message="provider failed secret-key-must-not-be-sent",
            )
        )
    result = deliver(settings, local_engine, ssl_context=context)
    assert result["uncertain" if lost else "accepted"] == 1
    assert len(server.messages) == 1
    assert b"secret-key-must-not-be-sent" not in server.messages[0]
    assert b"https://studio.technoinno.live/admin" in server.messages[0]
    assert deliver(settings, local_engine, ssl_context=context)["accepted"] == 0
    assert len(server.messages) == 1
    with sessions() as db:
        state = db.scalar(select(SystemSetting))
        assert state.value["stage"] == ("uncertain" if lost else "smtp_accepted")


def test_email_disabled_does_not_open_a_connection_or_capture_intent(local_engine, smtp):
    server, settings, context = smtp
    settings.alert_email_enabled = False
    assert deliver(settings, local_engine, ssl_context=context)["disabled_or_unconfigured"]
    assert server.messages == []
    with make_sessions(local_engine)() as db:
        assert db.scalar(select(SystemSetting)) is None


def test_recurring_launch_requires_backup_and_verified_outbound_alerts():
    from tsu.workflow import readiness

    settings = Settings(
        _env_file=None,
        spending_authorized=True,
        publishing_authorized=True,
        daily_budget_usd=2,
        monthly_budget_usd=60,
        production_times=("10:00", "19:00"),
        production_live_validated=True,
        youtube_long_lived_grant_confirmed=True,
        alert_email_enabled=True,
        smtp_host="smtp.example.invalid",
        smtp_user="synthetic",
        smtp_password="synthetic",
        smtp_from="studio@example.invalid",
    )
    assert set(readiness(settings)["blockers"]) == {
        "automatic_offhost_backup_not_confirmed",
        "outbound_alert_delivery_not_confirmed",
    }
    settings.offhost_backup_confirmed = settings.outbound_alerts_confirmed = True
    assert readiness(settings)["blockers"] == []
    settings.smtp_password = SecretStr("")
    assert "outbound_alert_delivery_not_confirmed" in readiness(settings)["blockers"]
