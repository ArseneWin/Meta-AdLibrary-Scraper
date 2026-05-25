#!/usr/bin/env python3
"""
Meta Ad Library Scraper
-----------------------
Searches Facebook's Ad Library for ads matching user-provided keywords
and saves the results to CSV.

Usage:
    python scraper.py --keywords "keyword1" "keyword2" --country IN
    python scraper.py --keywords-file my_keywords.txt --country US
    python scraper.py --keywords "solar panels" --resume
"""

import json
import time
import re
import os
import argparse
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import pandas as pd
from seleniumwire import webdriver
from selenium.webdriver.common.by import By


# ---------------------------------------------------------------------------
# Platform icon detection (based on Facebook's CSS sprite styles)
# ---------------------------------------------------------------------------
STYLE_TO_PLATFORM = {
    'mask-position: 0px -1184px': 'Facebook',
    'mask-position: -51px -357px': 'Instagram',
    'mask-position: -16px -528px': 'Audience Network',
    'mask-position: -29px -528px': 'Messenger',
    'mask-position: 0px -1197px': 'Threads',
}

HREF_CLASS = "xt0psk2.x1hl2dhg.xt0b8zv.x8t9es0.x1fvot60.xxio538.xjnfcd9.xq9mrsl.x1yc453h.x1h4wwuj.x1fcty0u"


# ---------------------------------------------------------------------------
# Browser setup
# ---------------------------------------------------------------------------
def setup_driver(headless: bool = False) -> webdriver.Chrome:
    """Launch a Chrome browser, optionally in headless (invisible) mode."""
    options = webdriver.ChromeOptions()

    if headless:
        options.add_argument('--headless')

    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')
    options.add_argument('--start-maximized')
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )

    return webdriver.Chrome(options=options)


# ---------------------------------------------------------------------------
# URL builder
# ---------------------------------------------------------------------------
def build_search_url(keyword: str, country: str = 'IN',
                     active_status: str = 'all',
                     start_date: Optional[str] = None) -> str:
    """Build a Facebook Ad Library search URL for a given keyword."""
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    params = {
        'active_status': active_status,
        'ad_type': 'all',
        'country': country,
        'is_targeted_country': 'false',
        'media_type': 'all',
        'q': keyword,
        'search_type': 'keyword_unordered',
        'start_date[min]': start_date,
    }

    return 'https://www.facebook.com/ads/library/?' + urllib.parse.urlencode(params)


# ---------------------------------------------------------------------------
# Data extraction helpers
# ---------------------------------------------------------------------------
def clean_text(text: str) -> str:
    """Strip excess whitespace and non-printable characters."""
    try:
        text = text.strip().encode('utf-8').decode('unicode_escape').encode('latin1').decode('utf-8')
    except Exception:
        text = text.strip()
    text = text.replace(',', ' ')
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\x20-\x7E]', '', text)
    return text.strip()


def is_valid_page_link(href: Optional[str]) -> bool:
    """Return True if the URL looks like a real social media page link."""
    if not href:
        return False

    skip = [
        '/ads/library/', '/search/', '/hashtag/', '/events/', '/photos/',
        '/videos/', '/posts/', '/pages/', '/groups/', '/marketplace/',
        'facebook.com/tr', 'facebook.com/sharer', '/help/', '/privacy/',
        '/terms/', '/watch/', '/gaming/', '/business/', '/developers/',
        '/careers/', '/about/', 'facebook.com/dialog', 'facebook.com/login',
    ]
    if any(p in href for p in skip):
        return False

    platforms = [
        'facebook.com/', 'instagram.com/', 'threads.net/',
        'twitter.com/', 'x.com/', 'linkedin.com/', 'youtube.com/',
        'tiktok.com/', 'telegram.me/', 't.me/',
    ]
    if not any(p in href for p in platforms):
        return False

    if '?' in href:
        query = href.split('?')[1]
        if any(p in query for p in ['fref=', 'ref=', 'hc_location=', '__tn__=']):
            return False

    return True


def clean_page_link(href: str) -> str:
    """Normalise a page URL (https, www, trailing slash)."""
    if not href:
        return ''

    clean = href.split('?')[0].split('#')[0]

    for domain in ['facebook.com', 'instagram.com', 'threads.net']:
        if domain in clean:
            if not clean.startswith('https://www.'):
                clean = re.sub(r'^https?://(www\.)?', '', clean)
                clean = 'https://www.' + clean
            break
    else:
        if not clean.startswith('https://'):
            clean = re.sub(r'^http://', 'https://', clean)
            if not clean.startswith('https://'):
                clean = 'https://' + clean

    if not clean.endswith('/'):
        clean += '/'

    return clean


def extract_page_link(element) -> str:
    """Try multiple strategies to pull a page URL out of an ad element."""
    # Strategy 1: specific CSS class used by Facebook for page links
    try:
        css = 'a.' + '.'.join(HREF_CLASS.split())
        for link in element.find_elements(By.CSS_SELECTOR, css):
            href = link.get_attribute('href')
            if href and is_valid_page_link(href):
                return clean_page_link(href)
    except Exception:
        pass

    # Strategy 2: aria-label containing "Page"
    try:
        for link in element.find_elements(By.CSS_SELECTOR, 'a[aria-label*="Page"]'):
            href = link.get_attribute('href')
            if href and is_valid_page_link(href):
                return clean_page_link(href)
    except Exception:
        pass

    # Strategy 3: direct social media links with a role="link"
    try:
        selector = (
            'a[href*="facebook.com/"][role="link"], '
            'a[href*="instagram.com/"][role="link"], '
            'a[href*="threads.net/"][role="link"]'
        )
        for link in element.find_elements(By.CSS_SELECTOR, selector):
            href = link.get_attribute('href')
            if href and is_valid_page_link(href):
                return clean_page_link(href)
    except Exception:
        pass

    return ''


def extract_ad_info(text: str, keyword: str) -> Dict[str, Any]:
    """Parse raw ad text into structured fields."""
    info: Dict[str, Any] = {
        'Keyword':    keyword,
        'Scraped_At': datetime.now().isoformat(),
    }

    # Active / Inactive status
    status = re.search(r'^(Inactive|Active)', text)
    info['Status'] = status.group(1) if status else ''

    # Library ID
    lib_id = re.search(r'Library ID:\s*(\d+)', text)
    info['Library_ID'] = lib_id.group(1) if lib_id else ''
    info['Ad_URL'] = (
        f"https://www.facebook.com/ads/library/?id={info['Library_ID']}"
        if info['Library_ID'] else ''
    )

    # Dates
    date_range = re.search(r'(\d{1,2} \w{3} \d{4}) - (\d{1,2} \w{3} \d{4})', text)
    started     = re.search(r'Started running on (\d{1,2} \w{3} \d{4})', text)

    if date_range:
        info['Start_Date'] = date_range.group(1)
        info['End_Date']   = date_range.group(2)
        try:
            d1 = datetime.strptime(info['Start_Date'], '%d %b %Y')
            d2 = datetime.strptime(info['End_Date'],   '%d %b %Y')
            info['Total_Active_Days'] = abs((d2 - d1).days)
        except Exception:
            info['Total_Active_Days'] = ''
    elif started:
        info['Start_Date']        = started.group(1)
        info['End_Date']          = 'Still active'
        info['Total_Active_Days'] = ''
    else:
        info['Start_Date'] = info['End_Date'] = ''
        info['Total_Active_Days'] = ''

    # Audience size
    audience = re.search(r'Estimated audience size:\s*\n(.*)', text)
    info['Estimated_Audience'] = audience.group(1).strip() if audience else ''

    # Amount spent
    amount = re.search(r'Amount spent \((\w+)\):\s*\n(.*)', text)
    if amount:
        info['Currency']       = amount.group(1)
        info['Amount_Spent']   = amount.group(2).strip()
    else:
        info['Currency']     = ''
        info['Amount_Spent'] = ''

    # Impressions
    impressions = re.search(r'Impressions:\s*\n(.*)', text)
    info['Impressions'] = impressions.group(1).strip() if impressions else ''

    # Page name
    sponsored = re.search(r'\n([^\n]+)\nSponsored', text)
    info['Page_Name'] = sponsored.group(1).strip() if sponsored else ''

    return info


def extract_ads_from_page(driver, keyword: str) -> List[Dict[str, Any]]:
    """Walk all ad cards currently loaded in the browser and extract data."""
    containers = driver.find_elements(
        By.CSS_SELECTOR,
        'div.xrvj5dj.x18m771g.x1p5oq8j.xp48ta0.x18d9i69.xtssl2i.xtqikln'
        '.x1na6gtj.x1jr1mh3.x15h0gye.x7sq92a.xlxr9qa'
    )
    print(f'  Found {len(containers)} ad containers.')

    ads = []
    for container in containers:
        for child in container.find_elements(By.XPATH, './*'):
            try:
                raw_text = child.text.strip()
                ad_info  = extract_ad_info(raw_text, keyword)

                # Full ad body text
                body_divs = child.find_elements(By.CSS_SELECTOR, 'div._4ik4._4ik5')
                ad_info['Ad_Text'] = ' '.join(
                    clean_text(d.text) for d in body_divs
                ).strip()

                # Platforms
                platforms = set()
                try:
                    icons = child.find_element(
                        By.CSS_SELECTOR,
                        '.x6s0dn4.x78zum5.x1q0g3np.x2lwn1j.xeuugli'
                    ).find_elements(By.CLASS_NAME, 'xtwfq29')
                    for icon in icons:
                        style = icon.get_attribute('style') or ''
                        for snippet, name in STYLE_TO_PLATFORM.items():
                            if snippet in style:
                                platforms.add(name)
                except Exception:
                    pass
                ad_info['Platforms'] = ', '.join(sorted(platforms))

                # Page link
                ad_info['Page_Link'] = extract_page_link(child)

                ads.append(ad_info)

            except Exception as e:
                print(f'  Warning: could not parse an ad card — {e}')
                continue

    return ads


# ---------------------------------------------------------------------------
# Progress tracking (simple, no risk/SEBI logic)
# ---------------------------------------------------------------------------
class ProgressTracker:
    def __init__(self, path: str = 'scraping_progress.json'):
        self.path = path
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.path):
            with open(self.path) as f:
                return json.load(f)
        return {'completed': [], 'total_ads': 0, 'started': datetime.now().isoformat()}

    def save(self):
        self.data['last_update'] = datetime.now().isoformat()
        with open(self.path, 'w') as f:
            json.dump(self.data, f, indent=2)

    def is_done(self, keyword: str) -> bool:
        return keyword in self.data['completed']

    def mark_done(self, keyword: str, count: int):
        if keyword not in self.data['completed']:
            self.data['completed'].append(keyword)
        self.data['total_ads'] += count
        self.save()

    def reset(self):
        if os.path.exists(self.path):
            os.remove(self.path)
        self.data = {'completed': [], 'total_ads': 0, 'started': datetime.now().isoformat()}


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------
def deduplicate(ads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate ads (by Library ID, or by content hash as fallback)."""
    import hashlib
    seen = set()
    unique = []
    for ad in ads:
        key = ad.get('Library_ID') or hashlib.md5(
            '|'.join([ad.get('Page_Name', ''), ad.get('Ad_Text', '')[:100]]).encode()
        ).hexdigest()
        if key not in seen:
            seen.add(key)
            unique.append(ad)
    removed = len(ads) - len(unique)
    if removed:
        print(f'  Removed {removed} duplicates. {len(unique)} unique ads remaining.')
    return unique


# ---------------------------------------------------------------------------
# Core scrape function
# ---------------------------------------------------------------------------
def scrape_keyword(keyword: str, country: str, max_scrolls: int,
                   headless: bool, start_date: Optional[str],
                   output_dir: str) -> List[Dict[str, Any]]:
    """Open the browser, scroll through results for one keyword, return ads."""
    url = build_search_url(keyword, country=country, start_date=start_date)
    print(f'\nSearching: "{keyword}"  |  URL: {url}')

    driver = None
    try:
        driver = setup_driver(headless=headless)
        driver.get(url)
        driver.execute_script("document.body.style.zoom='25%'")
        time.sleep(5)

        prev_requests = len(driver.requests)
        stale_count   = 0

        for scroll_num in range(1, max_scrolls + 1):
            driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
            time.sleep(3)

            current_requests = len(driver.requests)
            if current_requests == prev_requests:
                stale_count += 1
                if stale_count >= 3:
                    print(f'  No new content after {stale_count} attempts — stopping scroll.')
                    break
            else:
                stale_count = 0
                prev_requests = current_requests

            # Save intermediate results every 10 scrolls
            if scroll_num % 10 == 0:
                print(f'  Scroll {scroll_num}: saving intermediate results...')
                interim = extract_ads_from_page(driver, keyword)
                if interim:
                    _save_csv(interim, keyword, output_dir, tag=f'interim_{scroll_num}')

        ads = extract_ads_from_page(driver, keyword)
        return ads

    except Exception as e:
        print(f'  Error scraping "{keyword}": {e}')
        return []
    finally:
        if driver:
            driver.quit()


def _save_csv(ads: List[Dict[str, Any]], keyword: str,
              output_dir: str, tag: str = '') -> str:
    """Save a list of ads to a CSV file and return the path."""
    os.makedirs(output_dir, exist_ok=True)
    safe_kw   = re.sub(r'[^\w\- ]', '', keyword).strip().replace(' ', '_')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    suffix    = f'_{tag}' if tag else ''
    path      = os.path.join(output_dir, f'{safe_kw}{suffix}_{timestamp}.csv')
    pd.DataFrame(ads).to_csv(path, index=False)
    print(f'  Saved {len(ads)} ads → {path}')
    return path


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description='Scrape Facebook Ad Library for ads matching given keywords.'
    )

    kw_group = parser.add_mutually_exclusive_group(required=True)
    kw_group.add_argument(
        '--keywords', nargs='+', metavar='KEYWORD',
        help='One or more keywords to search, e.g. --keywords "solar panels" "EV cars"'
    )
    kw_group.add_argument(
        '--keywords-file', metavar='FILE',
        help='Path to a plain text file with one keyword per line'
    )

    parser.add_argument('--country',      default='IN',  help='Two-letter country code (default: IN)')
    parser.add_argument('--max-scrolls',  type=int, default=50, help='Max scroll attempts per keyword (default: 50)')
    parser.add_argument('--start-date',   metavar='YYYY-MM-DD', help='Only show ads started on or after this date')
    parser.add_argument('--output-dir',   default='results', help='Folder to save CSV results (default: results)')
    parser.add_argument('--headless',     action='store_true', help='Run browser invisibly')
    parser.add_argument('--resume',       action='store_true', help='Skip keywords already completed in a previous run')
    parser.add_argument('--fresh-start',  action='store_true', help='Ignore previous progress and start over')

    args = parser.parse_args()

    # Load keywords
    if args.keywords:
        keywords = args.keywords
    else:
        with open(args.keywords_file) as f:
            keywords = [line.strip() for line in f if line.strip()]

    print('=' * 60)
    print('Meta Ad Library Scraper')
    print('=' * 60)
    print(f'Keywords  : {keywords}')
    print(f'Country   : {args.country}')
    print(f'Max scrolls per keyword: {args.max_scrolls}')
    print(f'Output dir: {args.output_dir}')
    print('=' * 60)

    tracker = ProgressTracker()
    if args.fresh_start:
        tracker.reset()

    all_ads: List[Dict[str, Any]] = []

    for i, keyword in enumerate(keywords, 1):
        print(f'\n[{i}/{len(keywords)}] Keyword: "{keyword}"')

        if args.resume and tracker.is_done(keyword):
            print('  Already completed — skipping.')
            continue

        ads = scrape_keyword(
            keyword     = keyword,
            country     = args.country,
            max_scrolls = args.max_scrolls,
            headless    = args.headless,
            start_date  = args.start_date,
            output_dir  = args.output_dir,
        )

        if ads:
            ads = deduplicate(ads)
            _save_csv(ads, keyword, args.output_dir)
            tracker.mark_done(keyword, len(ads))
            all_ads.extend(ads)
            print(f'  ✓ {len(ads)} ads collected for "{keyword}"')
        else:
            print(f'  No ads found for "{keyword}"')

        time.sleep(2)  # polite pause between searches

    # Final consolidated file
    if all_ads:
        all_ads = deduplicate(all_ads)
        final_path = _save_csv(all_ads, 'ALL_KEYWORDS', args.output_dir)
        print(f'\n{"=" * 60}')
        print(f'Done! {len(all_ads)} unique ads saved to: {final_path}')
        print('=' * 60)
    else:
        print('\nNo ads were collected.')


if __name__ == '__main__':
    main()
