# simple-scraper

A straightforward tool to search Facebook's public Ad Library by keyword and save the results to CSV.

No risk scoring. No regulatory checks. Just ads.

> Part of the [meta-adlib-scraper](../) repository. Looking for the India financial ads + SEBI version? See [india-finads-risk-check](../india-finads-risk-check/).
>
> This tool was built alongside research into financial ad scams in India. See the report: [Money from Misery: How Meta Profits from & Exposes Indians to Scams](https://www.bard.edu/wwwmedia/files/6710304/1/Money%20from%20MiseryFinal%20v1.pdf) by Hamza Farooqui & Inayat Sabhikhi (April 2026), published in association with [Ekō](https://www.eko.org/), [Bard Human Rights Project](https://hrp.bard.edu/), and [Forum for Developing Communities](https://forumdc.org).

---

## What it does

1. Takes a list of keywords from you
2. Opens Facebook's Ad Library in a Chrome browser (automatically)
3. Scrolls through results for each keyword
4. Collects ad data — page name, ad text, platforms, dates, spend, audience size, page link
5. Saves everything to a CSV you can open in Excel

---

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Make sure you also have Chrome and a matching [ChromeDriver](https://chromedriver.chromium.org/downloads) installed.

---

## Usage

### Pass keywords directly

```bash
python scraper.py --keywords "solar panels" "electric vehicles" "online courses"
```

### Use a keywords file

Edit `keywords.txt` (one keyword per line), then run:

```bash
python scraper.py --keywords-file keywords.txt
```

### All options

| Option | What it does | Default |
|---|---|---|
| `--country XX` | Two-letter country code | `IN` (India) |
| `--max-scrolls N` | How far to scroll per keyword | `50` |
| `--start-date YYYY-MM-DD` | Only return ads started after this date | Last 30 days |
| `--output-dir PATH` | Folder to save results | `results/` |
| `--headless` | Run browser invisibly | Off |
| `--resume` | Skip keywords already completed in a previous run | Off |
| `--fresh-start` | Ignore previous progress and restart | Off |

### Examples

```bash
# Search in the US
python scraper.py --keywords "weight loss" --country US

# Run invisibly, custom output folder
python scraper.py --keywords-file keywords.txt --headless --output-dir my_data

# Resume an interrupted run
python scraper.py --keywords-file keywords.txt --resume
```

---

## Output

Results are saved in the `results/` folder:

- One CSV per keyword saved as it completes
- A final `ALL_KEYWORDS_*.csv` combining everything

### CSV columns

| Column | Description |
|---|---|
| `Keyword` | The keyword that found this ad |
| `Status` | Active or Inactive |
| `Library_ID` | Facebook's unique ID for the ad |
| `Ad_URL` | Direct link to the ad in Ad Library |
| `Page_Name` | Name of the page that ran the ad |
| `Page_Link` | Link to the advertiser's page |
| `Ad_Text` | Body text of the ad |
| `Platforms` | Facebook, Instagram, etc. |
| `Start_Date` | When the ad started running |
| `End_Date` | When it stopped (or "Still active") |
| `Total_Active_Days` | How long it ran |
| `Estimated_Audience` | Audience size range |
| `Currency` | Currency of reported spend |
| `Amount_Spent` | Spend range (e.g. ₹1,000 - ₹5,000) |
| `Impressions` | Impression range |
| `Scraped_At` | When this row was collected |

---

## Notes

- The browser window will open and scroll automatically. Use `--headless` to run it in the background.
- Results are saved every 10 scrolls, so data is not lost if the script is interrupted.
- Facebook's Ad Library is public — no API key required.

---

## License

MIT
