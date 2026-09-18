# Compliance & Scraping Ethics

Collecting job-postings data sits in a legal gray area. This project is for
**personal job search**. Follow these rules to stay ethical and reduce risk.

## 1. Prefer official APIs

- **Greenhouse / Lever / Ashby** expose public JSON endpoints used by their own
  job boards. Fetching these is lower-risk than HTML scraping.
- **RemoteOK / Remotive** document public APIs — use them.
- **Hacker News** has an official Firebase API — use it, never scrape HTML.
- **LinkedIn**: the public Jobs API is restricted to approved partners and
  scraping violates LinkedIn's ToS (and has led to litigation, e.g. *hiQ v.
  LinkedIn*). **Do not scrape LinkedIn.** Use manual search + saved alerts only.
- **Indeed**: heavy anti-bot (Cloudflare) and ToS forbids scraping; the
  Publisher API requires approval and is for job boards. Treat as manual.

## 2. Respect robots.txt and rate limits

- Check `robots.txt` before any HTML scrape.
- Apply conservative delays (≥ 1 req/sec), exponential backoff on 429/503.
- Rotate a descriptive `User-Agent` including contact info (see `.env.example`).
- Never bypass CAPTCHAs, login walls, or IP bans.

## 3. Do not scrape gated or paywalled content

- **FlexJobs** full listings are behind a subscription — do not scrape them
  unless you hold an account and comply with its terms.
- Do not scrape content behind authentication or that requires a profile
  (e.g. Blind, Hired.com full profiles).

## 4. Personal data (GDPR / CCPA)

- Store **only job-posting metadata**: title, company, location, salary range,
  description, URL, posting date. This is business/employment information, not
  personal data.
- Do **not** collect or store: applicant names, recruiter emails, candidate
  profiles, or any `PII` appearing in job text.
- If a posting embeds a personal contact, strip it during normalization.

## 5. Salary data

- Only public salary ranges are collected (many US states now mandate salary
  transparency). Crowdsourced comp (Levels.fyi, Blind) is used for
  benchmarking only, not redistributed.

## 6. Data use

- This is a **personal/educational** project. Do not resell scraped data,
  build a competing job board, or redistribute in bulk.
- Keep retention short (e.g. prune postings older than ~90 days) to avoid
  hosting stale/outdated listings.

## 7. Opt-in / consent where applicable

- If you ever expose this as a shared service, publish an attribution page and
  honor takedown requests from any source.

## TL;DR

> API-first. Respect robots.txt. Rate-limit. No PII. No paywalls. No LinkedIn
> scraping. Personal use only.
