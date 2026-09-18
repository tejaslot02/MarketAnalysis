"""Mine candidate skills from job descriptions for skill-bank enrichment.

High-precision approach: match a curated list of technical skill PHRASES
(exact, hyphen/slash-normalized) plus technical regex tokens (camelCase,
acronyms, delimited), then filter out known skills, company names, and noise.
Candidates are stored in `skill_candidates` for review/promotion.

Run ad hoc:  python flows/mine_skills.py
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from collections import Counter
from typing import Any

from prefect import flow, get_run_logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from dictionaries import load_dict

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/jobs",
)

SKILL_PHRASES = [
    "cross encoder", "dense retrieval", "sparse retrieval", "hybrid retrieval",
    "vector search", "semantic search", "hybrid search", "neural search",
    "approximate nearest neighbor", "nearest neighbor",
    "query expansion", "query understanding", "query rewriting", "query reformulation",
    "learning to rank", "collaborative filtering", "content based filtering",
    "two tower", "dual encoder", "recommendation engine", "recommendation system",
    "rank fusion", "reciprocal rank fusion", "ensemble retrieval",
    "query embedding", "document embedding", "passage retrieval", "document retrieval",
    "inverted index", "bm25", "tf idf",
    "retrieval augmented generation", "graph rag", "hybrid rag", "agentic rag",
    "multi agent", "agent orchestration", "tool calling", "function calling",
    "prompt tuning", "instruction tuning", "fine tuning", "reinforcement learning from human feedback",
    "direct preference optimization", "low rank adaptation",
    "knowledge graph", "graph neural network", "graph neural networks",
    "feature store", "model registry", "model monitoring", "drift detection",
    "data drift", "concept drift", "batch inference", "online inference",
    "real time inference", "model serving", "canary deployment", "shadow deployment",
    "blue green deployment", "feature engineering", "feature selection",
    "uplift modeling", "survival analysis", "causal inference", "causal machine learning",
    "time series forecasting", "bayesian inference", "bayesian optimization",
    "medallion architecture", "data mesh", "data fabric", "data lakehouse",
    "stream processing", "batch processing", "data lineage", "data governance",
    "named entity recognition", "text classification", "topic modeling",
    "sentiment analysis", "data storytelling", "data visualization",
]

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "in", "on", "for", "with", "to",
    "from", "by", "as", "at", "you", "your", "we", "our", "they", "their", "it",
    "its", "this", "that", "these", "those", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "can", "could", "should", "may", "might", "must", "work", "working", "team",
    "experience", "years", "year", "required", "requirements", "responsibilities",
    "skills", "qualifications", "role", "position", "job", "candidate", "company",
    "benefits", "salary", "remote", "hybrid", "full", "time", "part", "contract",
    "plus", "preferred", "nice", "bonus", "equal", "opportunity", "employer", "apply",
    "join", "help", "build", "new", "etc", "eg", "ie", "via", "per", "using", "use",
    "used", "including", "include", "includes", "may", "other", "related", "strong",
    "ability", "knowledge", "understanding", "across", "within", "such", "more",
    "about", "what", "why", "how", "when", "where", "who", "hiring", "great", "best",
    "excellent", "looking", "plus", "non", "us", "based",
}

GENERIC_ACRONYMS = {
    "ai", "ml", "ds", "bi", "api", "apis", "sdk", "db", "ci", "cd", "hr", "vp",
    "ceo", "cto", "coo", "cfo", "b2b", "b2c", "saas", "paas", "iaas", "ui", "ux",
    "qa", "seo", "roi", "kpi", "okr", "pm", "eng", "http", "https", "json", "xml",
    "csv", "yaml", "html", "css", "usd", "gmt", "est", "pst", "utc", "ft", "pt",
    "gtm", "pto", "nyc", "agi", "rrsp", "apac", "dpsp", "hra", "emed", "ivp",
    "ioi", "crm", "erp", "cms", "sla", "poc", "rfp", "yoe", "fte", "ctc", "ote",
    "sf", "la", "uk", "eu", "usa", "us", "ca", "tx", "ny", "wa", "ma", "il",
    "ba", "qa", "dev", "ops", "sre", "dba", "tpm", "em", "ic", "vp", "svp", "evp",
}

DELIMITED = re.compile(r"\b[a-z0-9]+(?:[./#\-][a-z0-9]+)+\b")
ACRONYM = re.compile(r"\b[A-Z]{2,6}\b")
CAMEL = re.compile(r"\b[a-z]+(?:[A-Z][a-z0-9]+)+\b|\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+\b")


def _known_skill_terms() -> set[str]:
    known: set[str] = set()
    skills_map = load_dict("skills_technologies.yaml").get("skills", {})
    for category, entries in skills_map.items():
        if category == "domain_specializations":
            for _sub, sub_entries in entries.items():
                for e in sub_entries:
                    known.add(e["name"].lower())
                    known.update(a.lower() for a in e.get("aliases", []))
        else:
            for e in entries:
                known.add(e["name"].lower())
                known.update(a.lower() for a in e.get("aliases", []))
    return known


def extract_candidates(text: str, known: set[str]) -> set[str]:
    candidates: set[str] = set()
    norm = re.sub(r"[-/]", " ", text.lower())

    for phrase in SKILL_PHRASES:
        if phrase in norm:
            candidates.add(phrase)

    low = text.lower()
    for m in CAMEL.findall(text):
        candidates.add(m.lower())
    for m in ACRONYM.findall(text):
        t = m.lower()
        if t not in GENERIC_ACRONYMS:
            candidates.add(t)
    return candidates


def _is_known(term: str, known: set[str]) -> bool:
    t = term.strip().lower()
    if t in known:
        return True
    if t.endswith("s") and t[:-1] in known:
        return True
    return (t + "s") in known


def is_candidate(term: str, known: set[str], blocked: set[str]) -> bool:
    t = term.strip().lower()
    if len(t) < 3 or len(t) > 45:
        return False
    if t in STOPWORDS or t in blocked or t in GENERIC_ACRONYMS:
        return False
    if any(w in blocked for w in t.split()):
        return False
    return not _is_known(t, known)


def _context(text: str, term: str, width: int = 90) -> str:
    idx = text.lower().find(term.lower())
    if idx < 0:
        return ""
    s = max(0, idx - width)
    e = min(len(text), idx + len(term) + width)
    return text[s:e].strip().replace("\n", " ")


@flow(name="mine-skills")
async def mine_skills_flow(min_freq: int = 3, top_n: int = 500) -> dict[str, int]:
    logger = get_run_logger()
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)

    known = _known_skill_terms()
    blocked: set[str] = set()

    # company names from master data + company board slugs
    async with engine.connect() as conn:
        comps = (await conn.execute(text("SELECT lower(name) AS n FROM companies"))).mappings().all()
        blocked.update(r["n"] for r in comps if r["n"])
        jd_rows = (await conn.execute(text(
            "SELECT title, description FROM jobs WHERE description IS NOT NULL AND description <> ''"
        ))).mappings().all()
    for slug in (load_dict("companies.yaml").get("ats", {}) or {}).values():
        for s in slug or []:
            blocked.add(str(s).lower())
    blocked.update({
        "linkedin", "indeed", "glassdoor", "greenhouse", "lever", "workable", "ashby",
        "wellfound", "remoteok", "remotive", "jobicy", "arbeitnow", "himalayas",
        "elevenagents", "elevencreative", "iconiq", "eleven",
    })

    freq: Counter[str] = Counter()
    contexts: dict[str, list[str]] = {}
    for r in jd_rows:
        jd_text = f"{r['title']} {r['description'] or ''}"
        for term in extract_candidates(jd_text, known):
            term = term.strip()
            if not is_candidate(term, known, blocked):
                continue
            freq[term] += 1
            if term not in contexts:
                contexts[term] = []
            if len(contexts[term]) < 3:
                ctx = _context(jd_text, term)
                if ctx:
                    contexts[term].append(ctx)

    ranked = [(t, c) for t, c in freq.items() if c >= min_freq]
    ranked.sort(key=lambda x: -x[1])
    ranked = ranked[:top_n]

    n = 0
    async with engine.begin() as conn:
        for term, count in ranked:
            await conn.execute(text("""
                INSERT INTO skill_candidates (term, frequency, sample_contexts, last_seen_at)
                VALUES (:term, :freq, CAST(:ctx AS jsonb), now())
                ON CONFLICT (term) DO UPDATE SET
                    frequency = EXCLUDED.frequency,
                    sample_contexts = EXCLUDED.sample_contexts,
                    last_seen_at = now()
            """), {"term": term, "freq": count, "ctx": json.dumps(contexts.get(term, []))})
            n += 1

    await engine.dispose()
    logger.info("Mined %d candidate skills (freq>=%d) from %d JDs", n, min_freq, len(jd_rows))
    return {"candidates": n, "jds": len(jd_rows)}


if __name__ == "__main__":
    print(asyncio.run(mine_skills_flow()))
