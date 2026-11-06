from fastapi.testclient import TestClient

from tsu.api import create_app
from tsu.config import Settings

TOKEN = "private-draft-owner-password-at-least-32-characters"


def test_google_information_pages_require_owner_until_publication_approval(local_engine):
    settings = Settings(_env_file=None, admin_token=TOKEN)
    client = TestClient(create_app(settings, local_engine))
    for path in ("/about", "/privacy", "/terms"):
        assert client.get(path).status_code == 401
        draft = client.get(path, headers={"Authorization": "Bearer " + TOKEN})
        assert draft.status_code == 200 and "Brouillon privé" in draft.text
        assert TOKEN not in draft.text
    settings.public_information_approved = True
    for path in ("/about", "/privacy", "/terms"):
        published = client.get(path)
        assert published.status_code == 200 and "Brouillon privé" not in published.text
    assert client.get("/admin").status_code == 401
    assert client.get("/api/overview").status_code == 401
