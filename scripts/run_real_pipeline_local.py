"""Direct live execution of the ETL pipeline on real job postings from the internet.

Fetches live job postings, normalizes schema, runs domain enrichment (salary, title,
seniority, skills, responsibilities), and mines technical skill trends.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Paths bootstrap
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "flows"))
sys.path.insert(0, str(REPO_ROOT / "scrapers"))
os.environ["DICTIONARY_DIR"] = str(REPO_ROOT / "data" / "dictionaries")

import httpx
from flows.transform import transform_record
from scrapers.portals.common import base_record, extract_salary, is_remote_text, stable_id, strip_html


def fetch_arbeitnow_jobs() -> list[dict]:
    print("[1/4] Fetching live jobs from Arbeitnow API...")
    url = "https://www.arbeitnow.com/api/job-board-api"
    try:
        resp = httpx.get(url, timeout=15.0)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        print(f"      Successfully retrieved {len(data)} raw job postings from Arbeitnow.")
        
        canonical_jobs = []
        for item in data:
            slug = item.get("slug", "")
            title = item.get("title", "")
            company = item.get("company_name", "")
            desc_html = item.get("description", "")
            desc = strip_html(desc_html)
            remote = bool(item.get("remote")) or is_remote_text(title, desc)
            s_min, s_max = extract_salary(desc)
            
            job = base_record(
                id=stable_id("arbeitnow", slug),
                source="arbeitnow",
                external_id=slug,
                title=title,
                company=company,
                location=item.get("location", "Remote"),
                is_remote=remote,
                remote_type="fully_remote" if remote else "onsite",
                salary_min=s_min,
                salary_max=s_max,
                salary_raw=f"${s_min} - ${s_max}" if s_min and s_max else None,
                posted_at=str(item.get("created_at")),
                description=desc,
                url=item.get("url", ""),
            )
            canonical_jobs.append(job)
        return canonical_jobs
    except Exception as exc:
        print(f"      [WARN] Failed to fetch from Arbeitnow: {exc}")
        return []


def fetch_remotive_jobs() -> list[dict]:
    print("[2/4] Fetching live Data & AI jobs from Remotive API...")
    url = "https://remotive.com/api/remote-jobs?category=data"
    try:
        resp = httpx.get(url, timeout=15.0)
        resp.raise_for_status()
        data = resp.json().get("jobs", [])
        print(f"      Successfully retrieved {len(data)} raw data/AI jobs from Remotive.")
        
        canonical_jobs = []
        for item in data:
            ext_id = str(item.get("id", ""))
            title = item.get("title", "")
            company = item.get("company_name", "")
            desc_html = item.get("description", "")
            desc = strip_html(desc_html)
            raw_salary = item.get("salary") or ""
            s_min, s_max = extract_salary(raw_salary + " " + desc)
            
            job = base_record(
                id=stable_id("remotive", ext_id),
                source="remotive",
                external_id=ext_id,
                title=title,
                company=company,
                location=item.get("candidate_required_location", "Remote"),
                is_remote=True,
                remote_type="fully_remote",
                salary_min=s_min,
                salary_max=s_max,
                salary_raw=raw_salary or None,
                posted_at=str(item.get("publication_date")),
                description=desc,
                url=item.get("url", ""),
            )
            canonical_jobs.append(job)
        return canonical_jobs
    except Exception as exc:
        print(f"      [WARN] Failed to fetch from Remotive: {exc}")
        return []


def run_real_pipeline():
    start_time = time.time()
    print("=" * 70)
    print("STARTING LIVE REAL PIPELINE EXECUTION (EXTRACT -> TRANSFORM -> ENRICH)")
    print("=" * 70)
    
    # 1. Extract stage
    raw_jobs = []
    raw_jobs.extend(fetch_arbeitnow_jobs())
    raw_jobs.extend(fetch_remotive_jobs())
    
    if not raw_jobs:
        print("[ERROR] No jobs retrieved. Check internet connectivity.")
        sys.exit(1)
        
    print(f"\n[3/4] Running Core Transformation & Domain Enrichment on {len(raw_jobs)} jobs...")
    enriched_jobs = []
    
    # 2. Transform stage
    for r in raw_jobs:
        try:
            enriched = transform_record(r)
            enriched_jobs.append(enriched)
        except Exception as exc:
            print(f"      [SKIP] Error enriching job {r.get('id')}: {exc}")
            
    print(f"      Enrichment complete for {len(enriched_jobs)} jobs.")
    
    # 3. Analyze & Export stage
    print("\n[4/4] Analyzing Job Postings & Saving Enriched Output...")
    
    data_dir = REPO_ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    out_file = data_dir / "real_jobs_enriched.json"
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(enriched_jobs, f, indent=2, default=str)
    print(f"      Saved all {len(enriched_jobs)} enriched records to: {out_file}")
    
    # Statistics
    total = len(enriched_jobs)
    remote_count = sum(1 for j in enriched_jobs if j.get("is_remote"))
    above_150k = sum(1 for j in enriched_jobs if j.get("salary_ok"))
    with_canonical_title = sum(1 for j in enriched_jobs if j.get("title_canonical"))
    with_skills = sum(1 for j in enriched_jobs if len(j.get("skills", [])) > 0)
    with_seniority = sum(1 for j in enriched_jobs if j.get("seniority"))
    
    print("\n" + "=" * 70)
    print("LIVE PIPELINE RUN RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Total Live Postings Ingested    : {total}")
    print(f"  Remote Postings                : {remote_count} ({(remote_count/total)*100:.1f}%)")
    print(f"  Postings with Canonical DS/AI   : {with_canonical_title}")
    print(f"  Postings with Detected Seniority: {with_seniority}")
    print(f"  Postings with Extracted Skills  : {with_skills}")
    print(f"  Postings Meeting $150K+ USD     : {above_150k}")
    print(f"  Total Execution Time            : {time.time() - start_time:.2f}s")
    print("=" * 70)
    
    # Print sample of top enriched jobs
    print("\nSAMPLE OF EXTRACTED AND ENRICHED JOBS:")
    print("-" * 70)
    sample_jobs = [j for j in enriched_jobs if j.get("title_canonical") or j.get("skills")][:5]
    for idx, j in enumerate(sample_jobs, 1):
        skills_str = ", ".join(s["name"] for s in j.get("skills", [])[:5]) or "None"
        print(f"Job #{idx}:")
        print(f"  Title     : {j.get('title')}")
        print(f"  Canonical : {j.get('title_canonical') or 'N/A'}")
        print(f"  Company   : {j.get('company')}")
        print(f"  Seniority : {j.get('seniority') or 'N/A'}")
        print(f"  Salary    : {j.get('salary_raw') or (str(j.get('salary_min')) + '-' + str(j.get('salary_max')) if j.get('salary_min') else 'Not specified')}")
        print(f"  Above 150k: {j.get('salary_ok')}")
        print(f"  Skills    : {skills_str}")
        print(f"  URL       : {j.get('url')}")
        print("-" * 70)


if __name__ == "__main__":
    run_real_pipeline()
