.PHONY: up down logs ps init-prefect migrate seed-master prefect-flows seed-db scrape scrape-remoteok scrape-all venv test reset clean

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f $(SVC)

ps:
	docker compose ps

init-prefect:
	docker compose run --rm prefect-init

# Apply master-data schema (idempotent) for existing volumes
migrate:
	docker compose exec -T postgres psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-jobs} < db/init/02_master_data.sql
	docker compose exec -T postgres psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-jobs} < db/init/03_analytics.sql
	docker compose exec -T postgres psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-jobs} < db/init/04_skill_mining.sql

# Seed master data (portals/skills/titles/companies) from the YAML dictionaries
seed-master:
	docker compose exec -T prefect-scheduler python /opt/prefect/flows/seed_master_data.py

# Run the consume-raw-jobs flow ad hoc inside the scheduler
prefect-flows:
	docker compose exec -T prefect-scheduler python /opt/prefect/flows/scrape_flow.py

# Seed sample job rows into Postgres
seed-db:
	docker compose exec -T postgres psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-jobs} < db/seed/sample_jobs.sql

# Run a single spider (Extract) -- e.g. make scrape SPIDER=remoteok
scrape:
	docker compose run --rm scraper scrapy crawl $(SPIDER) $(ARGS)

scrape-remoteok:
	docker compose run --rm scraper scrapy crawl remoteok

# Run ALL configured portal spiders (fan-out over companies.yaml)
scrape-all:
	docker compose exec -T prefect-scheduler python /opt/prefect/flows/scrape_portals.py

# Create a local virtualenv + install dev/test deps (see docs/TEST_CASES.md)
venv:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements-dev.txt

# Run the ETL unit test suite (see docs/TEST_CASES.md)
test:
	.venv/bin/python -m pytest tests/ -v

reset:
	docker compose down -v
	docker compose build --no-cache

clean:
	docker compose down -v --remove-orphans
