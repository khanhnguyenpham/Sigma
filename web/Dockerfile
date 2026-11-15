FROM node:24-bookworm-slim AS frontend
WORKDIR /build/web/frontend
COPY web/frontend/package.json web/frontend/package-lock.json ./
RUN npm ci
COPY web/frontend/index.html web/frontend/tsconfig.json web/frontend/vite.config.ts ./
COPY web/frontend/src ./src
COPY web/frontend/public ./public
COPY web/backend/configs/m3-profile.json /build/web/backend/configs/m3-profile.json
RUN npm run build

FROM python:3.12-slim-bookworm AS application
ARG SIGMA_RELEASE_VERSION=""
ENV M3_RELEASE_VERSION=$SIGMA_RELEASE_VERSION
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY web/deploy/requirements-runtime.txt /app/web/deploy/requirements-runtime.txt
RUN python -m pip install --no-cache-dir -r web/deploy/requirements-runtime.txt
COPY web/backend/pyproject.toml web/backend/alembic.ini /app/web/backend/
COPY web/backend/src /app/web/backend/src
COPY web/backend/migrations /app/web/backend/migrations
COPY web/backend/scripts /app/web/backend/scripts
COPY web/backend/configs/*.json /app/web/backend/configs/
COPY M2/models /app/M2/models
COPY M2/final_report.py /app/M2/final_report.py
COPY src /app/src
COPY data/configs/config.json data/configs/m2-reproduce.json data/configs/m2-final.json /app/data/configs/
COPY --from=frontend /build/web/frontend/dist /app/web/frontend/dist
RUN python -m pip install --no-cache-dir --no-deps -e web/backend && python -m pip check \
    && useradd --uid 10001 --create-home sigma \
    && mkdir -p /srv/outputs /srv/source/data && chown -R sigma:sigma /srv/outputs
USER sigma
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)"
CMD ["python", "-m", "uvicorn", "main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--limit-concurrency", "64"]
