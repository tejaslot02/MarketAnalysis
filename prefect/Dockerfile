# Custom Prefect image for the job-search platform.
# Base: official Prefect 3.x (ships prefect + SQLAlchemy + alembic).
# Adds the runtime deps used by the ETL flows (flows/). Pinned requirements
# live in requirements.txt to avoid transitive-version breakage (e.g. Twisted).
FROM prefecthq/prefect:3.2.14-python3.12

WORKDIR /opt/prefect

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
