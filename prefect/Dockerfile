# Custom Prefect image for the job-search platform.
# Base: official Prefect 3.x (already ships prefect + SQLAlchemy + alembic).
# Adds the runtime deps used by the ETL flow (flows/scrape_flow.py + transform.py):
#   redis         -> Dragonfly (Redis Streams) client
#   asyncpg       -> async Postgres driver
#   elasticsearch -> ES 8.x client (search index load)
#   minio         -> S3-compatible client (raw archive load)
#   PyYAML        -> parse the dictionaries in data/dictionaries/
FROM prefecthq/prefect:3.2.14-python3.12

RUN pip install --no-cache-dir \
    redis==5.0.8 \
    "asyncpg>=0.29.0" \
    elasticsearch==8.13.2 \
    minio==7.2.7 \
    PyYAML==6.0.1

# Scrapy (runs the portal spiders from flows/scrape_portals.py)
RUN pip install --no-cache-dir "scrapy==2.11.2" "Twisted==23.10.0"
