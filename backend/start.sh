#!/bin/sh
# Container entrypoint.
#
# Lives in a script rather than in CMD because some managed hosts pass their
# "docker command" override through as exec-form argv, which turns `&&` into a
# literal argument instead of shell syntax. A script is parsed by the shell
# regardless of how the platform invokes it.
set -e

alembic upgrade head

# Free managed tiers offer no separate worker process, so the API container can
# host one. Leave START_WORKER unset wherever a dedicated worker service runs
# (docker-compose, the VPS) — two workers on one broker would both claim jobs.
if [ "${START_WORKER:-0}" = "1" ]; then
    echo "start.sh: running an in-process Celery worker (START_WORKER=1)"
    celery -A app.workers.celery_app.celery_app worker \
        --concurrency="${CELERY_CONCURRENCY:-1}" \
        --max-tasks-per-child=20 \
        --loglevel=warning &
fi

# exec so uvicorn becomes PID 1 and receives the platform's stop signals.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
