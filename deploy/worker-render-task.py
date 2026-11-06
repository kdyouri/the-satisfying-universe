"""Isolated validation queue only; no production or provider operation is performed."""

import contextlib
import io
import json
import runpy
from pathlib import Path

from tsu.worker import celery_app


@celery_app.task(name="tsu.validate_worker_render", acks_late=False, ignore_result=True)
def validate_worker_render():
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        runpy.run_path("/data/validation/verify-workflow-render.py", run_name="__main__")
    result = json.loads(output.getvalue())
    result["actual_celery_prefork_task"] = True
    report = Path("/data/validation/worker-render-report.json")
    temporary = report.with_suffix(".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n")
    temporary.replace(report)
