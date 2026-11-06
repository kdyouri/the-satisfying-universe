"""Read-only native-audio deployment checks: no provider request, job creation or upload."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import requests
from sqlalchemy import func, select

from tsu.config import Settings
from tsu.db import make_engine, make_sessions
from tsu.models import ModelUsage, ProductionJob, Publication, VideoGeneration
from tsu.native_profile import MODEL, native_profile
from tsu.workflow import ProductionWorkflow, readiness

EXPECTED = {'tsu/native_profile.py': '4c55503b98ae80f98d6f7a8ac2d247bcbee3e2b2bf23cd42869e953f9c507ec5', 'tsu/native_production.py': '9fcfc6f53f1e186945bc80e23e0392ad6771fe5400eb856d1db5a00f1cdb915e', 'tsu/workflow.py': '74351bbf49a80b8728da0a32a01fbf0f9590a4e523eab0bb9f15b8d41850b32b', 'tsu/pilot.py': 'a71b783f8f51f218a4dab872b8cb86bdeeb9b904128bc2582cc7b6c99a6d9af7', 'tsu/media.py': 'ac095a69a0ac9a631ddc0c5c6dd22147edc4d88bb8efebe447f391afd59dde36', 'tsu/config.py': '584f1776d25641ab3796962bdb02e3ac70547504ac0e733274ba01124d6bc7a9', 'tsu/production.py': '75fcc6b93c801de4f9463b31894f7e5e8686555971ea297fca0f28ec19a2d8d8', 'tsu/youtube_upload.py': '5f3bfcd5fe89a40de3a3ed035fc41560d7b57623331707e6ccfd2f8a07387c04', 'tsu/youtube_job.py': 'b610017e722b63a15c6894647a7d0b395bb8f2b5fcdbdf4e743099d813c36326', 'tsu/trial.py': '5656608f19b54f11196ca49b2cfb9499b60159f663aeab5bfd85aad63326165a', 'tsu/admin.html': '963bb40ff7c78c21d07d886f3b3200e50a43e3d054332cd0d4ae2ebb685d8059'}
actual = {p: hashlib.sha256(Path('/app', p).read_bytes()).hexdigest() for p in EXPECTED}
assert actual == EXPECTED and EXPECTED
s = Settings()
assert s.video_model == MODEL
assert not any((s.enable_daily_scheduler, s.spending_authorized, s.publishing_authorized,
                s.production_live_validated, s.alert_email_enabled, s.offhost_backup_confirmed,
                s.outbound_alerts_confirmed))
assert s.daily_budget_usd == s.monthly_budget_usd == 0
assert s.youtube_long_lived_grant_confirmed and s.public_information_approved
headers = {'Authorization': 'Bearer ' + s.admin_token.get_secret_value()}
base = 'http://127.0.0.1:8000'
admin = requests.get(base + '/admin', headers=headers, timeout=15)
assert admin.status_code == 200 and 'son IA natif' in admin.text and 'aucun assemblage' in admin.text
profile = requests.get(base + '/api/overview', headers=headers, timeout=15).json()['capabilities']['production_profile']
assert profile == native_profile()
assert requests.get(base + '/login', timeout=15).status_code == 200
html = requests.get(base + '/admin', headers={'Accept':'text/html'}, timeout=15, allow_redirects=False)
assert html.status_code == 303 and html.headers['Location'] == '/login'
assert requests.get(base + '/api/overview', timeout=15).status_code == 401
for page in ('/about','/privacy','/terms'):
    assert requests.get(base + page, timeout=15).status_code == 200
engine = make_engine(s.database_url.get_secret_value())
try:
    with make_sessions(engine)() as db:
        counts = {model.__tablename__: db.scalar(select(func.count()).select_from(model))
                  for model in [ModelUsage, ProductionJob, Publication, VideoGeneration]}
        assert counts == {'model_usage':18, 'production_jobs':3, 'publications':2,
                          'video_generations':6}
        actual_cost = db.scalar(select(func.sum(ModelUsage.actual_usd)))
        held = db.scalar(select(func.sum(ModelUsage.reserved_usd)).where(ModelUsage.actual_usd.is_(None)))
        assert (actual_cost,held) == (Decimal('2.402445'),Decimal('0.300000'))
        job = db.get(ProductionJob,'8db44bfd-f1b1-4433-a6ab-f4be088fc6da')
        assert job.status == 'cancelled' and job.payload['never_publish']
        assert job.payload['owner_discarded'] and not job.payload['private_trial_authorization']['confirmed']
        assert not db.scalar(select(Publication).where(Publication.video_id == job.payload['result']['video_id']))
    # This stops before provider creation because the owner discarded the job.
    blocked = ProductionWorkflow(s,engine,provider_factory=lambda: (_ for _ in ()).throw(AssertionError('No provider allowed'))).run(job.id)
    assert blocked['status'] == 'cancelled'
    print(json.dumps({'source_hashes':actual, 'source_hashes_match':True, 'future_profile':profile,
                      'discarded_job_blocked':True, 'readiness':readiness(s), 'counts':counts,
                      'confirmed_usd_preserved':str(actual_cost), 'held_usd_preserved':str(held),
                      'verification_paid_requests':0, 'new_uploads':0, 'real_emails_sent':0},indent=2))
finally:
    engine.dispose()
