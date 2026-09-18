"""Provision Metabase: admin user, Postgres data source, cards, and a dashboard.

Run inside a container on the jobs-net network:
    docker compose exec -T prefect-scheduler python - < scripts/setup_metabase.py
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE = os.getenv("METABASE_URL", "http://metabase:3000")
EMAIL = os.getenv("METABASE_ADMIN_EMAIL", "admin@example.com")
PASSWORD = os.getenv("METABASE_ADMIN_PASSWORD", "admin12345")

CARDS = [
    ("Total Jobs", "scalar", "SELECT COUNT(*) AS value FROM jobs"),
    ("Above 150K", "scalar", "SELECT COUNT(*) AS value FROM jobs WHERE salary_ok"),
    ("Remote Jobs", "scalar", "SELECT COUNT(*) AS value FROM jobs WHERE is_remote"),
    ("Jobs by Title", "bar", "SELECT COALESCE(title_canonical, 'Unclassified') AS title, COUNT(*) AS count FROM jobs GROUP BY 1 ORDER BY 2 DESC"),
    ("Jobs by Seniority", "pie", "SELECT COALESCE(seniority, 'unknown') AS seniority, COUNT(*) AS count FROM jobs GROUP BY 1 ORDER BY 2 DESC"),
    ("Jobs by Source", "bar", "SELECT source, COUNT(*) AS count FROM jobs GROUP BY 1 ORDER BY 2 DESC"),
    ("Top Skills", "bar", "SELECT s->>'name' AS skill, COUNT(*) AS count FROM jobs, jsonb_array_elements(skills) AS s GROUP BY 1 ORDER BY 2 DESC LIMIT 20"),
    ("150K+ Remote Jobs", "table", "SELECT title, company, title_canonical, seniority, salary_min, salary_max, url FROM jobs WHERE salary_ok AND is_remote ORDER BY salary_max DESC NULLS LAST"),
    ("Skills Frequency (Top 25)", "table", "SELECT skill, category, job_count, avg_weight FROM skill_frequency ORDER BY job_count DESC LIMIT 25"),
    ("Top Skill Pairs", "table", "SELECT skill_a || ' <-> ' || skill_b AS pair, co_count FROM skill_cooccurrence ORDER BY co_count DESC LIMIT 20"),
    ("Portal Freshness", "table", "SELECT portal, MAX(finished_at) AS last_run, COALESCE(SUM(jobs_emitted),0) AS jobs, COUNT(*) FILTER (WHERE status='error') AS errors FROM portal_runs GROUP BY 1 ORDER BY 2 DESC NULLS LAST"),
    ("Companies Tracked", "scalar", "SELECT COUNT(*) AS value FROM companies"),
    ("New Jobs Last 7 Days", "scalar", "SELECT COUNT(*) AS value FROM jobs WHERE first_seen_at >= now() - interval '7 days'"),
    ("Jobs by Track", "bar", "SELECT COALESCE(t.track, 'unclassified') AS track, COUNT(*) AS count FROM jobs j LEFT JOIN job_titles t ON t.canonical = j.title_canonical GROUP BY 1 ORDER BY 2 DESC"),
    ("Skill Momentum", "table", "SELECT skill, first_count, latest_count, delta, pct_change FROM skill_momentum WHERE pct_change IS NOT NULL ORDER BY delta DESC LIMIT 20"),
    ("Top Skills (latest)", "table", "SELECT skill, job_count FROM skill_trend WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM skill_trend) ORDER BY job_count DESC LIMIT 25"),
    ("Company Hiring Velocity", "table", "SELECT company, jobs_active, jobs_new FROM company_hiring WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM company_hiring) ORDER BY jobs_new DESC, jobs_active DESC LIMIT 20"),
    ("Title Mix (latest)", "table", "SELECT title_canonical, job_count FROM title_trend WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM title_trend) ORDER BY job_count DESC LIMIT 20"),
    ("Salary Benchmarks", "table", "SELECT title, seniority, n, avg_min, avg_max, min_salary, max_salary FROM salary_benchmark ORDER BY n DESC"),
]


def req(method, path, data=None, session=None):
    url = BASE + path
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(url, data=body, method=method)
    r.add_header("Content-Type", "application/json")
    if session:
        r.add_header("X-Metabase-Session", session)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            txt = resp.read().decode() or "{}"
            return resp.status, json.loads(txt)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]


def main():
    _, props = req("GET", "/api/session/properties")

    if not props.get("has-user-setup"):
        st, out = req("POST", "/api/setup", {
            "token": props.get("setup-token"),
            "user": {"first_name": "Admin", "last_name": "User", "email": EMAIL, "password": PASSWORD},
            "prefs": {"site_name": "Job Search", "site_locale": "en", "allow_tracking": False},
        })
        print(f"[setup] admin created status={st}")
    else:
        print("[setup] admin already exists")

    st, out = req("POST", "/api/session", {"username": EMAIL, "password": PASSWORD})
    session = out.get("id") if isinstance(out, dict) else None
    print(f"[login] status={st} session={bool(session)}")
    if not session:
        print("FATAL: no session", out)
        return

    db_id = None
    st, dbs = req("GET", "/api/database", session=session)
    for d in (dbs.get("data") or []):
        if d.get("name") == "Jobs DB":
            db_id = d.get("id")
            break
    if db_id is None:
        st, db = req("POST", "/api/database", {
            "name": "Jobs DB",
            "engine": "postgres",
            "details": {"host": "postgres", "port": 5432, "dbname": "jobs", "user": "postgres", "password": "postgres", "ssl": False},
            "is_full_sync": True,
            "is_on_demand": False,
        }, session=session)
        db_id = db.get("id") if isinstance(db, dict) else None
        print(f"[database] created id={db_id} status={st}")
    else:
        print(f"[database] exists id={db_id}")

    existing_names = set()
    st, existing = req("GET", "/api/card?f=all", session=session)
    for c in (existing or []):
        if isinstance(c, dict) and c.get("name"):
            existing_names.add(c["name"])

    card_ids = []
    for name, display, query in CARDS:
        if name in existing_names:
            print(f"[card] '{name}' exists, skip")
            continue
        st, card = req("POST", "/api/card", {
            "name": name,
            "dataset_query": {"database": db_id, "type": "native", "native": {"query": query, "template-tags": {}}},
            "display": display,
            "visualization_settings": {},
        }, session=session)
        cid = card.get("id") if isinstance(card, dict) else None
        card_ids.append(cid)
        print(f"[card] '{name}' id={cid} status={st}")

    dash_id = None
    st, dashboards = req("GET", "/api/dashboard", session=session)
    for d in (dashboards or []):
        if isinstance(d, dict) and d.get("name") == "DS/AI/ML Job Market":
            dash_id = d.get("id")
            break
    if dash_id is None:
        st, dash = req("POST", "/api/dashboard", {"name": "DS/AI/ML Job Market"}, session=session)
        dash_id = dash.get("id") if isinstance(dash, dict) else None
        print(f"[dashboard] created id={dash_id} status={st}")
    else:
        print(f"[dashboard] exists id={dash_id}")

    # Metabase v0.49 removed POST /api/dashboard/:id/cards; use PUT to set the
    # full ordered card layout (idempotent: rebuild the list from card names).
    st, all_cards = req("GET", "/api/card?f=all", session=session)
    name_to_id = {}
    for c in (all_cards or []):
        if isinstance(c, dict) and c.get("name"):
            name_to_id[c["name"]] = c.get("id")

    layout = []
    col = 0
    for i, (name, _display, _query) in enumerate(CARDS, start=1):
        cid = name_to_id.get(name)
        if cid:
            # Metabase v0.49 schema: negative id = new dashcard; card_id = card id.
            layout.append({"id": -i, "card_id": cid, "size_x": 4, "size_y": 4, "row": 0, "col": col})
            col += 4
    st, _ = req("PUT", f"/api/dashboard/{dash_id}/cards", {"cards": layout}, session=session)
    print(f"[dashboard] set {len(layout)} cards status={st}")

    print(f"\nDONE. Dashboard URL: {BASE}/dashboard/{dash_id}")
    print(f"Login: {EMAIL} / {PASSWORD}")


if __name__ == "__main__":
    main()
