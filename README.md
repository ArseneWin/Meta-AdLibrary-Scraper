# meta-adlib-scraper

A collection of tools for scraping Facebook's public Ad Library.

This repository contains two tools built for different purposes. Both use the same underlying approach — automating a Chrome browser to collect ad data from [Facebook's Ad Library](https://www.facebook.com/ads/library/) — but they differ significantly in scope and output.

---

## Research

The `india-finads-risk-check` tool was developed as part of the following report:

**[Money from Misery: How Meta Profits from & Exposes Indians to Scams](https://www.bard.edu/wwwmedia/files/6710304/1/Money%20from%20MiseryFinal%20v1.pdf)**
*Hamza Farooqui & Inayat Sabhikhi — April 2026*

Published in association with [Ekō](https://www.eko.org/), [Bard Human Rights Project](https://hrp.bard.edu/), and [Forum for Developing Communities](https://forumdc.org).

The report investigates how Meta profits from fraudulent investment advertising in India, tests compliance with SEBI's advertiser verification requirements, and finds that 97% of financial advertisers on Meta are unregistered entities. The scraping tool in this repository was used to collect and analyse the advertising data underpinning those findings.

---

## Tools at a glance

| | [simple-scraper](./simple-scraper/) | [india-finads-risk-check](./india-finads-risk-check/) |
|---|---|---|
| **Purpose** | General-purpose ad collection | Financial ad monitoring for India |
| **Who it's for** | Anyone who wants ad data for any topic | Researchers and regulators tracking investment advertising |
| **Keywords** | You provide any keywords you like | Pre-built list of investment/trading-related terms |
| **Country** | Configurable (any country) | India (`IN`) focused |
| **Risk scoring** | ✗ | ✓ Scores ads LOW / MEDIUM / HIGH / CRITICAL |
| **SEBI check** | ✗ | ✓ Cross-references advertisers against SEBI's database |
| **Output** | Clean CSV with core ad fields | CSV with 50+ fields including risk and regulatory data |
| **Complexity** | Single file, minimal setup | Multi-file system with async processing |

---

## Which one should I use?

**Use `simple-scraper` if you want to:**
- Collect ads on any topic (products, services, campaigns, competitors, etc.)
- Work in any country
- Get a clean, straightforward CSV without extra analysis

**Use `india-finads-risk-check` if you want to:**
- Monitor financial and investment advertising on Facebook/Instagram in India
- Automatically flag ads using high-risk or scam-like language
- Check whether advertisers are registered with SEBI
- Produce a research or compliance dataset

---

## Repository structure

```
meta-adlib-scraper/
├── README.md                        ← You are here
├── simple-scraper/                  ← General-purpose scraper
│   ├── README.md
│   ├── scraper.py
│   ├── keywords.txt
│   ├── requirements.txt
│   └── .gitignore
└── india-finads-risk-check/         ← India financial ads + SEBI risk tool
    ├── README.md
    ├── enhanced_main.py
    ├── main.py
    ├── data_utils.py
    ├── sebi.py
    ├── sebi_enhanced.py
    ├── demo.py
    ├── enhanced_keywords.json
    ├── requirements.txt
    └── .gitignore
```

---

## Requirements (both tools)

- Python 3.9+
- Google Chrome installed
- ChromeDriver matching your Chrome version → [download here](https://chromedriver.chromium.org/downloads)

---

## License

MIT
