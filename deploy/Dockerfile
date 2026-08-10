# Single image for the whole backend (api + ml + agent). Locally these are split
# across two conda envs only because of a pre-existing Python 3.8 env constraint on
# the dev machine — that constraint doesn't exist in Docker, so here everything
# runs on one Python 3.11 interpreter and the API's subprocess call to the agent
# (api/routes/investigations.py) just points AGENT_PYTHON_BIN at `python` itself.
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-ml-api.txt agent/requirements.txt ./
RUN pip install --no-cache-dir -r requirements-ml-api.txt -r requirements.txt

COPY api/ api/
COPY agent/ agent/
COPY ml/ ml/
COPY data/generators/ data/generators/
COPY data/__init__.py data/__init__.py
COPY data/processed/ data/processed/

ENV PYTHONUNBUFFERED=1 \
    AGENT_PYTHON_BIN=python \
    API_BASE_URL=http://localhost:8000

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
