# india-finads-risk-check

A tool to monitor financial and investment advertising on Facebook and Instagram in India, with automatic risk scoring and SEBI registration checks.

> Part of the [meta-adlib-scraper](../) repository. Looking for a simpler, general-purpose scraper? See [simple-scraper](../simple-scraper/).

---

## Research

This tool was developed as part of the following report:

**[Money from Misery: How Meta Profits from & Exposes Indians to Scams](https://www.bard.edu/wwwmedia/files/6710304/1/Money%20from%20MiseryFinal%20v1.pdf)**
*Hamza Farooqui & Inayat Sabhikhi — April 2026*

Published in association with [Ekō](https://www.eko.org/), [Bard Human Rights Project](https://hrp.bard.edu/), and [Forum for Developing Communities](https://forumdc.org).

The report investigates how Meta profits from fraudulent investment advertising in India, tests compliance with SEBI's advertiser verification requirements, and finds that 97% of financial advertisers on Meta are unregistered entities. This tool was used to collect and analyse the advertising data underpinning those findings.

---

## What it does

1. **Scrapes Meta Ad Library** for investment-related ads in India using a pre-built list of keywords across categories like cryptocurrency, forex, stock tips, and more
2. **Risk-scores every ad** — flags language like "guaranteed returns", Telegram/WhatsApp links, suspiciously short campaigns, and other patterns associated with financial scams
3. **Checks SEBI registration** — looks up each advertiser page name against SEBI's database of registered investment intermediaries
4. **Exports a detailed CSV** with 50+ fields per ad, ready for research or compliance review

---

## Who it's for

Researchers, journalists, and regulatory teams monitoring unregistered or potentially fraudulent investment advertising on social media in India.

---

## File structure

| File | Purpose |
|---|---|
| `enhanced_main.py` | Main scraper — run this to collect ads |
| `main.py` | Original, simpler version of the scraper |
| `data_utils.py` | Helper classes: deduplication, risk scoring, progress tracking |
| `sebi_enhanced.py` | SEBI registration checker (async, faster) |
| `sebi.py` | SEBI checker (original version) |
| `demo.py` | Feature demonstration — no scraping required |
| `enhanced_keywords.json` | Keywords organised by scam category |

---

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

You also need Chrome and a matching [ChromeDriver](https://chromedriver.chromium.org/downloads).

---

## Usage

### Run the scraper

```bash
# Start a fresh session
python enhanced_main.py

# Resume an interrupted session
python enhanced_main.py --resume

# Target a specific category only
python enhanced_main.py --ad-type "Cryptocurrency"

# Quick test with limited scrolling
python enhanced_main.py --max-scrolls 10 --headless
```

### Check SEBI registration

Run this after scraping to cross-reference all advertiser pages against SEBI's database:

```bash
python sebi_enhanced.py
```

### See a demo of the features (no scraping)

```bash
python demo.py
```

---

## Output

| File | Description |
|---|---|
| `scraped_data/` | Incremental CSVs saved during scraping |
| `scraped_data/*_master.csv` | Consolidated file per keyword category |
| `final_investment_scam_ads_*.csv` | Final deduplicated output with risk scores |
| `pages_analysis.csv` | Per-advertiser summary with SEBI status |
| `scraping_progress.json` | Auto-saved progress for resume functionality |

### Risk levels

Each ad is assigned one of four risk levels:

| Level | Score | Meaning |
|---|---|---|
| `LOW` | 0–2 | No significant red flags |
| `MEDIUM` | 3–4 | Some concerning language or patterns |
| `HIGH` | 5–7 | Multiple red flags |
| `CRITICAL` | 8+ | Strong indicators of a fraudulent ad |

---

## Notes

- SEBI database lookups are rate-limited (max 5 concurrent requests) to be respectful to their servers.
- Progress is saved every 10 scrolls — interrupted sessions can be resumed with `--resume`.
- Do **not** commit `scraped_data/`, output CSVs, or `scraping_progress.json` to version control — these are excluded by `.gitignore`.

---

## License

MIT
