.PHONY: up down logs ps init-prefect prefect-flows seed-db scrape scrape-remoteok reset clean

# Start the full stack (detached)
up:
	docker compose up -d

# Stop the stack (keep volumes)
down:
	docker compose down

# Follow logs; usage: make logs SVC=scraper (omit SVC for all)
logs:
	docker compose logs -f $(SVC)

# Show service status
ps:
	docker compose ps

# Run Prefect DB migrations (also runs automatically on first `up`)
init-prefect:
	docker compose run --rm prefect-init

# Run the consume-raw-jobs flow ad hoc inside the Prefect worker
prefect-flows:
	docker compose exec -T prefect-worker python /opt/prefect/flows/scrape_flow.py

# Seed sample job rows into Postgres
seed-db:
	docker compose exec -T postgres psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-jobs} < db/seed/sample_jobs.sql

# Run a spider (Extract) -- greenhouse | remoteok | lever | hn
scrape:
	docker compose run --rm scraper scrapy crawl greenhouse -a board_token=companyname

# RemoteOK extract (self-contained; no args needed)
scrape-remoteok:
	docker compose run --rm scraper scrapy crawl remoteok

# Full reset: stop, remove volumes, rebuild images
reset:
	docker compose down -v
	docker compose build --no-cache

# Tear down everything including orphaned containers and volumes
clean:
	docker compose down -v --remove-orphans
