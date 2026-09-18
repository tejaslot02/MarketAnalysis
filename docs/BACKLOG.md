# Backlog

Current state: **8,124 jobs across 9 portals** (greenhouse, ashby, arbeitnow,
jobicy, remoteok, workingnomads, weworkremotely, himalayas, remotive).

## Near-term (prioritized)

- [ ] HN "Who is hiring?" spider — auto-discover the monthly thread via the
      HN Algolia API; ~500-1000 jobs/mo (remote + comp), no API key needed.
- [ ] Fix Lever spider — all 7 boards return 0; `api.lever.co/v0/postings/{company}`
      appears stale/deprecated. Investigate endpoint / fallback to HTML.
- [ ] Correct ~17 wrong ATS tokens in `data/dictionaries/companies.yaml`
      (snowflake, doordash, uber, square, shopify, spotify, github, confluent,
      hashicorp, anduril, cohere, palantir; ashby: vercel, mistral, replicate, together).
- [ ] Greenhouse description enrichment pass — run with `-a fetch_details=true`
      (rate-limited, background) to backfill `description` for greenhouse jobs.

## Medium-term

- [ ] Adzuna API portal (needs free API key).
- [ ] HTML portals (best-effort): remote.co, mljobs.io, deeplearning.ai jobs.
- [ ] Salary data quality: normalize to annual USD, drop hourly/low/foreign values.
- [ ] Cross-source dedup (same role on Greenhouse + aggregators).
- [ ] LLM description enrichment: extract salary (when regex fails),
      must-have vs nice-to-have skills, YoE, team, visa/remote constraints.
- [ ] Profile matching + skill-gap report (populate pgvector `embedding` column,
      cosine-rank jobs vs resume/skills).

## Later / ideas

- [ ] Alerts on new matches (email/Slack/Discord) after each consume run.
- [ ] Application tracker (CRM): applied / interview / offer / follow-up.
- [ ] Salary benchmarking vs Levels.fyi.
- [ ] Company hiring-velocity signals (funding, headcount).
- [ ] Spark batch for dedup/enrichment (currently Python-only).
- [ ] Lightweight web UI (Streamlit/Next.js) + CSV export.
