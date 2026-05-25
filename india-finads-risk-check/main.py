from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time
import urllib.parse
from collections import defaultdict
from seleniumwire.utils import decode
import re
from datetime import datetime

import pandas as pd

data_to_export = {}
style2platform = {
    "width: 12px; height: 12px; mask-image: url(\"https://static.xx.fbcdn.net/rsrc.php/v4/yU/r/UGsQosxvBYw.png\"); mask-size: 21px 1388px; mask-position: 0px -1184px;": "Facebook",
    "width: 12px; height: 12px; mask-image: url(\"https://static.xx.fbcdn.net/rsrc.php/v4/yk/r/U_jVQXVKYJP.png\"); mask-size: 73px 387px; mask-position: -51px -357px;": "Instagram",
    "width: 12px; height: 12px; mask-image: url(\"https://static.xx.fbcdn.net/rsrc.php/v4/yQ/r/-FzqMKJCYcu.png\"); mask-size: 90px 596px; mask-position: -16px -528px;": "Audience Network",
    "width: 12px; height: 12px; mask-image: url(\"https://static.xx.fbcdn.net/rsrc.php/v4/yQ/r/-FzqMKJCYcu.png\"); mask-size: 90px 596px; mask-position: -29px -528px;": "Messenger",
    "width: 12px; height: 12px; mask-image: url(\"https://static.xx.fbcdn.net/rsrc.php/v4/yU/r/UGsQosxvBYw.png\";); mask-size: 21px 1388px; mask-position: 0px -1197px;": "Threads"
}

href_class = "xt0psk2.x1hl2dhg.xt0b8zv.x8t9es0.x1fvot60.xxio538.xjnfcd9.xq9mrsl.x1yc453h.x1h4wwuj.x1fcty0u"

def search_keyword(url, keyword, ad):

    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # Uncomment to run in headless mode
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--start-maximized')
    # Add performance optimizations
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')

    driver = webdriver.Chrome(options=options)

    print(f"Navigating to {url}")
    driver.get(url)
    # Set zoom to 25% to show more ads on screen for better efficiency
    driver.execute_script("document.body.style.zoom='25%'")
    time.sleep(5)  # wait for initial load

    SCROLL_PAUSE_TIME = 3  # Reduced from 5 to 3 seconds for faster scrolling

    # Keep track of network calls
    prev_request_count = len(driver.requests)

    while True:
        # Scroll to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)  # wait for network activity

        # Get new number of requests
        current_request_count = len(driver.requests)

        if current_request_count == prev_request_count:
            print("No new network calls detected. Stopping scroll.")
            break
        else:
            print(f"New calls detected: {current_request_count - prev_request_count}")
            prev_request_count = current_request_count

    divs = get_all_ad_divs(driver, keyword, ad)
    # graphql = get_graphql_calls(driver)
    return divs

def extract_ad_info(text, keyword, ad):
    info = {}

    info["Ad"] = ad
    info["Keyword"] = keyword

    # 1. Status
    status_match = re.search(r'^(Inactive|Active)', text)
    info["Status"] = status_match.group(1) if status_match else None

    # 2. Library ID
    lib_id_match = re.search(r'Library ID:\s*(\d+)', text)
    info["Library ID"] = lib_id_match.group(1) if lib_id_match else ''
    info["Ad URL"] = f"https://www.facebook.com/ads/library/?id={info['Library ID']}"

    # 3. Start Date & 4. End Date
    date_range_match = re.search(r'(\d{1,2} \w{3} \d{4}) - (\d{1,2} \w{3} \d{4})', text)
    start_single_date_match = re.search(r'Started running on (\d{1,2} \w{3} \d{4})', text)

    if date_range_match:
        info["Start Date"] = date_range_match.group(1)
        info["End Date"] = date_range_match.group(2)

        date1 = datetime.strptime(info["Start Date"], "%d %b %Y")
        date2 = datetime.strptime(info["End Date"], "%d %b %Y")

        info["Total Active Days"] = abs((date2 - date1).days)
    elif start_single_date_match:
        info["Start Date"] = start_single_date_match.group(1)
        info["End Date"] = ''
        info["Total Active Days"] = ''
    else:
        info["Start Date"] = info["End Date"] = ''
        info["Total Active Days"] = ''

    # 5. Estimated audience size
    audience_match = re.search(r'Estimated audience size:\s*\n(.*)', text)
    info["Estimated audience size"] = audience_match.group(1).strip() if audience_match else ''

    # 6. Amount spent (INR)
    amount_match = re.search(r'Amount spent \(INR\):\s*\n(.*)', text)
    info["Amount spent (INR)"] = amount_match.group(1).strip() if amount_match else ''

    # 7. Impressions
    impressions_match = re.search(r'Impressions:\s*\n(.*)', text)
    info["Impressions"] = impressions_match.group(1).strip() if impressions_match else ''

    # 8. Page Name — look for line before "Sponsored", or fallback to repeating names at the bottom
    sponsored_match = re.search(r'\n([^\n]+)\nSponsored', text)
    if sponsored_match:
        info["Page Name"] = sponsored_match.group(1).strip()
    else:
        # Fallback: look for lines repeated twice (common pattern in Meta ads)
        lines = text.splitlines()
        candidates = [line for line in lines if lines.count(line.strip()) > 1 and len(line.strip()) > 3]
        info["Page Name"] = candidates[0].strip() if candidates else ''

    return info

def is_valid_page_link(href):
    """Check if the href is a valid page link (Facebook, Instagram, or other social platforms)"""
    if not href:
        return False
    
    # Handle Facebook redirects to other platforms
    if 'l.facebook.com/l.php' in href:
        try:
            # Extract the actual URL from Facebook redirect
            parsed_url = urllib.parse.urlparse(href)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            if 'u' in query_params:
                actual_url = urllib.parse.unquote(query_params['u'][0])
                return is_valid_page_link(actual_url)  # Recursively check the actual URL
        except:
            pass
    
    # Skip ad library links, search results, and other non-page links
    skip_patterns = [
        '/ads/library/', '/search/', '/hashtag/', '/events/', '/photos/',
        '/videos/', '/posts/', '/pages/', '/groups/', '/marketplace/',
        'facebook.com/tr', 'facebook.com/sharer',
        '/help/', '/privacy/', '/terms/', '/watch/', '/gaming/',
        '/business/', '/developers/', '/careers/', '/about/',
        'facebook.com/dialog', 'facebook.com/login', 'facebook.com/recover'
    ]
    
    for pattern in skip_patterns:
        if pattern in href:
            return False
    
    # Check for supported platforms
    supported_platforms = [
        'facebook.com/', 'instagram.com/', 'threads.net/',
        'twitter.com/', 'x.com/', 'linkedin.com/',
        'youtube.com/', 'tiktok.com/', 'telegram.me/', 't.me/'
    ]
    
    platform_found = False
    for platform in supported_platforms:
        if platform in href:
            platform_found = True
            break
    
    if not platform_found:
        return False
    
    # Skip URLs with query parameters that indicate non-page links
    if '?' in href:
        query_part = href.split('?')[1]
        if any(param in query_part for param in ['fref=', 'ref=', 'hc_location=', '__tn__=']):
            return False
    
    # Facebook-specific validation
    if 'facebook.com/' in href:
        try:
            # Extract the path part
            url_parts = href.replace('https://www.facebook.com/', '').replace('http://www.facebook.com/', '')
            url_parts = url_parts.replace('https://facebook.com/', '').replace('http://facebook.com/', '')
            url_parts = url_parts.replace('https://m.facebook.com/', '').replace('http://m.facebook.com/', '')
            
            # Remove parameters and trailing slash for analysis
            path_part = url_parts.split('?')[0].split('#')[0].strip('/')
            
            # Should have at least a username/id part and not be too deep
            if path_part and len(path_part) > 0:
                # Split by slash to check depth
                path_segments = path_part.split('/')
                
                # Valid page links usually have 1-2 segments: username or username/section
                if len(path_segments) <= 2:
                    # First segment should be a valid username or page ID
                    first_segment = path_segments[0]
                    if len(first_segment) > 0 and not first_segment.startswith('.'):
                        return True
        except:
            pass
    
    # For other platforms, basic validation
    elif any(platform in href for platform in ['instagram.com/', 'threads.net/', 'twitter.com/', 'x.com/']):
        # Basic validation for other social platforms
        if len(href.strip()) > 10:  # Minimum length check
            return True
    
    return False

def clean_page_link(href):
    """Clean and normalize the page link for any supported platform"""
    if not href:
        return ""
    
    # Handle Facebook redirects first
    if 'l.facebook.com/l.php' in href:
        try:
            parsed_url = urllib.parse.urlparse(href)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            if 'u' in query_params:
                actual_url = urllib.parse.unquote(query_params['u'][0])
                return clean_page_link(actual_url)  # Recursively clean the actual URL
        except:
            pass
    
    # Remove parameters and normalize
    clean_href = href.split('?')[0].split('#')[0]
    
    # Platform-specific cleaning
    if 'facebook.com' in clean_href:
        # Ensure it starts with https://www.facebook.com/
        if not clean_href.startswith('https://www.facebook.com/'):
            if clean_href.startswith('http://www.facebook.com/'):
                clean_href = clean_href.replace('http://', 'https://')
            elif clean_href.startswith('facebook.com/'):
                clean_href = 'https://www.' + clean_href
            elif clean_href.startswith('www.facebook.com/'):
                clean_href = 'https://' + clean_href
    
    elif 'instagram.com' in clean_href:
        # Ensure it starts with https://www.instagram.com/
        if not clean_href.startswith('https://www.instagram.com/'):
            if clean_href.startswith('http://www.instagram.com/'):
                clean_href = clean_href.replace('http://', 'https://')
            elif clean_href.startswith('instagram.com/'):
                clean_href = 'https://www.' + clean_href
            elif clean_href.startswith('www.instagram.com/'):
                clean_href = 'https://' + clean_href
    
    elif 'threads.net' in clean_href:
        # Ensure it starts with https://www.threads.net/
        if not clean_href.startswith('https://www.threads.net/'):
            if clean_href.startswith('http://www.threads.net/'):
                clean_href = clean_href.replace('http://', 'https://')
            elif clean_href.startswith('threads.net/'):
                clean_href = 'https://www.' + clean_href
            elif clean_href.startswith('www.threads.net/'):
                clean_href = 'https://' + clean_href
    
    # For other platforms, ensure https://
    elif not clean_href.startswith('https://'):
        if clean_href.startswith('http://'):
            clean_href = clean_href.replace('http://', 'https://')
        else:
            clean_href = 'https://' + clean_href
    
    # Ensure trailing slash for consistency
    if not clean_href.endswith('/'):
        clean_href += '/'
    
    return clean_href


def clean_text(text):
    # Remove excessive whitespace, newlines, and non-printable characters
    cleaned = text.strip().encode('utf-8').decode('unicode_escape').encode('latin1').decode('utf-8')
    cleaned = cleaned.replace(',', ' ')
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = re.sub(r'[^\x20-\x7E]', '', cleaned)
    
    return cleaned.strip()


def get_all_ad_divs(driver, keyword, ad):
    # Get divs by class    
    target_divs = driver.find_elements(By.CSS_SELECTOR,
    "div.xrvj5dj.x18m771g.x1p5oq8j.xp48ta0.x18d9i69.xtssl2i.xtqikln.x1na6gtj.x1jr1mh3.x15h0gye.x7sq92a.xlxr9qa"
    )
    print(f"Found {len(target_divs)} matching divs.")

    all_divs = []

    try:
        for i, div in enumerate(target_divs):
            children = div.find_elements(By.XPATH, "./*")
            div_data = []

            for j, child in enumerate(children):
                ad_text = child.text.strip().encode('utf-8').decode('unicode_escape').encode('latin1').decode('utf-8')
                ad_deetz = extract_ad_info(ad_text, keyword, ad)

                # Get all text in divs with class "_4ik4 _4ik5"
                ik4_divs = child.find_elements(By.CSS_SELECTOR, 'div._4ik4._4ik5')
                ik4_texts = "\n".join([clean_text(ik4_div.text) for ik4_div in ik4_divs])
                ad_deetz["FullText"] = ik4_texts
                platforms_set = set()
                platforms = child.find_element(By.CSS_SELECTOR, '.x6s0dn4.x78zum5.x1q0g3np.x2lwn1j.xeuugli')\
                    .find_elements(By.CLASS_NAME, "xtwfq29")
                for platform in platforms:
                    style = platform.get_attribute("style")
                    if style and style in style2platform:
                        platforms_set.add(style2platform[style])
                ad_deetz["Platforms"] = list(platforms_set)
                
                # Extract PageLink - look for the advertiser's page link (Facebook, Instagram, etc.)
                page_link = ""
                
                # Strategy 1: Use the specific CSS class for href links (most reliable)
                try:
                    # Convert space-separated class list to CSS selector format
                    css_selector = 'a.' + '.'.join(href_class.split())
                    specific_links = child.find_elements(By.CSS_SELECTOR, css_selector)
                    for link in specific_links:
                        href = link.get_attribute('href')
                        if href and is_valid_page_link(href):
                            page_link = clean_page_link(href)
                            break
                except Exception as e:
                    # If the specific selector fails, continue to next strategy
                    pass
                
                # Strategy 2: Look for links with aria-label containing "Page"
                if not page_link:
                    try:
                        page_links = child.find_elements(By.CSS_SELECTOR, 'a[aria-label*="Page"], a[aria-label*="page"]')
                        for link in page_links:
                            href = link.get_attribute('href')
                            if href and is_valid_page_link(href):
                                page_link = clean_page_link(href)
                                break
                    except:
                        pass
                
                # Strategy 3: Look for links in the sponsor/page name area with specific patterns
                if not page_link:
                    try:
                        # Look for the page name link (usually appears near "Sponsored")
                        page_name_links = child.find_elements(By.CSS_SELECTOR, 'a[href*="facebook.com/"][role="link"], a[href*="instagram.com/"][role="link"], a[href*="threads.net/"][role="link"]')
                        for link in page_name_links:
                            href = link.get_attribute('href')
                            if href and is_valid_page_link(href):
                                # Check if this link appears near the page name or sponsor text
                                link_text = link.text.strip()
                                if link_text and len(link_text) > 2:  # Has meaningful text (likely page name)
                                    page_link = clean_page_link(href)
                                    break
                    except:
                        pass
                
                # Strategy 4: Look for Facebook redirect links (l.facebook.com)
                if not page_link:
                    try:
                        redirect_links = child.find_elements(By.CSS_SELECTOR, 'a[href*="l.facebook.com/l.php"]')
                        for link in redirect_links:
                            href = link.get_attribute('href')
                            if href and is_valid_page_link(href):
                                page_link = clean_page_link(href)
                                break
                    except:
                        pass
                
                # Strategy 5: Fallback - look for any valid page link
                if not page_link:
                    all_links = child.find_elements(By.CSS_SELECTOR, 'a[href]')
                    for link in all_links:
                        href = link.get_attribute('href')
                        if href and is_valid_page_link(href):
                            page_link = clean_page_link(href)
                            break
                
                ad_deetz["PageLink"] = page_link
                div_data.append(ad_deetz)

            all_divs = all_divs + div_data
    except Exception as e:
        print(f"Error occurred while processing divs: {e}")
    return all_divs

def get_graphql_calls(driver):

    output = defaultdict(list)
    for i, request in enumerate(driver.requests):
        
        if request.response:
            # Check for GraphQL characteristics:
            # 1. URL path contains 'graphql'
            # 2. Request method is POST
            # 3. Content-Type is application/json (common for GraphQL)
            # 4. Attempt to parse the body and check for 'query' field
            if 'graphql' in request.url and request.method == 'POST' and \
            request.headers.get('referer') and 'https://www.facebook.com/ads/library/' in request.headers['referer'] and\
                request.headers.get('x-fb-friendly-name'):
                key = request.headers['x-fb-friendly-name']
                body = decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity'))
                json_data = json.loads(body)
                output[key].append(json_data)

    return output


if __name__ == "__main__":

    facebook_ad_library_endpoint = "https://www.facebook.com/ads/library/"
    active_status = "all"
    ad_type = "all"
    country = "IN"

    ad_keyword_json = None
    with open("./keywords.json") as f:
        ad_keyword_json = json.load(f)

    all_output = []
    for ad, keywords in ad_keyword_json.items():
        # For each add
        ad_outputs = []
        safe_filename = re.sub(r'[^a-zA-Z0-9_\- ]+', '', ad)
        for keyword in keywords:
            try:
                encoded_keyword = urllib.parse.quote(keyword)
                target_url = f"{facebook_ad_library_endpoint}?active_status={active_status}&ad_type={ad_type}&country={country}&is_targeted_country=false&media_type=all&q={encoded_keyword}&search_type=keyword_unordered&start_date[min]=2025-09-01"
                divs = search_keyword(target_url, keyword, ad)
                ad_outputs = ad_outputs + divs
                # break
            except Exception as e:
                print(e)
                # raise e
        all_output +=  ad_outputs


        df = pd.DataFrame(ad_outputs)
        df.to_csv(f'./{safe_filename}.csv', index=False)
        
    df = pd.DataFrame(all_output)
    df.to_csv('./output.csv', index=False)
    
    # import json
    # with open('data.json', 'w') as f:
    #     json.dump(captured_graphql_calls, f)
