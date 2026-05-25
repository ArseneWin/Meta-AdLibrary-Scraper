import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
import numpy as np
import ast
import time
import aiohttp
import asyncio
from typing import List, Dict, Any

async def search_page_in_sebi_async(session, page_name, headers):
    """Search a page name in SEBI database and return if it exists (async version)"""
    url = "https://www.sebi.gov.in/sebiweb/ajax/other/getrecognisedintm.jsp"
    payload = {
        "intmId": "-1",
        "search": page_name,
        "regNo": ""
    }
    
    try:
        async with session.post(url, data=payload, headers=headers) as response:
            response.raise_for_status()
            text = await response.text()
            
            # Parse the HTML response
            soup = BeautifulSoup(text, 'html.parser')
            card_tables = soup.find_all('div', class_='fixed-table-body card-table')
            
            # If we found any records, the page exists in SEBI database
            return len(card_tables) > 0
            
    except Exception as e:
        print(f"Error searching for {page_name}: {e}")
        return False

def search_page_in_sebi(page_name, headers):
    """Search a page name in SEBI database and return if it exists"""
    url = "https://www.sebi.gov.in/sebiweb/ajax/other/getrecognisedintm.jsp"
    payload = {
        "intmId": "-1",
        "search": page_name,
        "regNo": ""
    }
    
    try:
        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()
        
        # Parse the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')
        card_tables = soup.find_all('div', class_='fixed-table-body card-table')
        
        # If we found any records, the page exists in SEBI database
        return len(card_tables) > 0
        
    except requests.exceptions.RequestException as e:
        print(f"Error searching for {page_name}: {e}")
        return False

async def search_all_pages_async(pages_df, headers):
    """Search all pages in SEBI database asynchronously"""
    print(f"Starting async search for {len(pages_df)} pages...")
    
    # Create a semaphore to limit concurrent requests (be respectful to the API)
    semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
    
    async def search_with_semaphore(session, page_name, page_idx):
        async with semaphore:
            print(f"Searching {page_idx+1}/{len(pages_df)}: {page_name}")
            result = await search_page_in_sebi_async(session, page_name, headers)
            # Small delay to be respectful to the API
            await asyncio.sleep(0.1)
            return result
    
    connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = []
        for idx, row in pages_df.iterrows():
            page_name = row['Page Name']
            task = search_with_semaphore(session, page_name, idx)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Exception for page {i}: {result}")
                processed_results.append(False)
            else:
                processed_results.append(result)
        
        return processed_results

def parse_platforms(platforms_str):
    """Parse the platforms string and return a list"""
    try:
        # Handle cases where platforms is already a list or a string representation of a list
        if pd.isna(platforms_str):
            return []
        if isinstance(platforms_str, str):
            # Try to evaluate as a Python literal (list)
            try:
                return ast.literal_eval(platforms_str)
            except:
                # If that fails, treat as a single platform
                return [platforms_str.strip()]
        return platforms_str if isinstance(platforms_str, list) else [str(platforms_str)]
    except:
        return []

# Read and analyze the CSV data
print("Reading Telegram-linked Investment Scams CSV...")
df = pd.read_csv('Telegram-linked Investment Scams.csv')

print(f"Original data shape: {df.shape}")
print(f"Columns: {df.columns.tolist()}")

# Convert Total Active Days to numeric, handling NaN values
df['Total Active Days'] = pd.to_numeric(df['Total Active Days'], errors='coerce')

# Parse platforms column
df['Platforms_List'] = df['Platforms'].apply(parse_platforms)

# Create individual platform columns
all_platforms = set()
for platforms_list in df['Platforms_List']:
    all_platforms.update(platforms_list)

print(f"Found platforms: {sorted(all_platforms)}")

# Create boolean columns for each platform
for platform in all_platforms:
    df[f'{platform}_ads'] = df['Platforms_List'].apply(lambda x: platform in x)

# Group by Page Name and PageLink
print("\nGrouping data by Page Name and PageLink...")
grouped_data = []

for (page_name, page_link), group in df.groupby(['Page Name', 'PageLink']):
    row_data = {
        'Page Name': page_name,
        'PageLink': page_link,
        'total_ads': len(group),
        'active_ads': len(group[group['Status'] == 'Active']),
        'inactive_ads': len(group[group['Status'] != 'Active'])
    }
    
    # Count ads per platform
    for platform in all_platforms:
        row_data[f'{platform}_ad_count'] = group[f'{platform}_ads'].sum()
    
    # Calculate average total active days (excluding active ads as requested)
    inactive_ads_with_days = group[(group['Status'] != 'Active') & (group['Total Active Days'].notna())]
    if len(inactive_ads_with_days) > 0:
        row_data['avg_active_days'] = inactive_ads_with_days['Total Active Days'].mean()
    else:
        row_data['avg_active_days'] = 0
    
    grouped_data.append(row_data)

# Create the grouped dataframe
pages_df = pd.DataFrame(grouped_data)
print(f"\nGrouped data shape: {pages_df.shape}")
print(f"Unique pages found: {len(pages_df)}")

# Search each page name in SEBI database
print("\nSearching page names in SEBI database...")
print("This may take a while as we need to make API calls for each page...")

pages_df['sebi_exists'] = False

# Use the same headers as before for consistency
sebi_headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:141.0) Gecko/20100101 Firefox/141.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Referer": "https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doRecognised=yes",
    "Content-type": "application/x-www-form-urlencoded",
    "Origin": "https://www.sebi.gov.in",
    "DNT": "1",
    "Connection": "keep-alive",
    # "Cookie": "JSESSIONID=...",  # Add your session cookie here if needed
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-GPC": "1",
    "Priority": "u=0"
}

# Search for each page using async calls for better performance
start_time = time.time()
sebi_results = asyncio.run(search_all_pages_async(pages_df, sebi_headers))
end_time = time.time()

# Assign results to the dataframe
pages_df['sebi_exists'] = sebi_results

print(f"\nAsync search completed in {end_time - start_time:.2f} seconds")
print(f"Average time per search: {(end_time - start_time) / len(pages_df):.3f} seconds")

# Save the pages info as CSV
output_filename = 'pages_analysis.csv'
pages_df.to_csv(output_filename, index=False)

print(f"\nPages analysis saved to {output_filename}")
print(f"Summary:")
print(f"- Total unique pages: {len(pages_df)}")
print(f"- Pages found in SEBI database: {pages_df['sebi_exists'].sum()}")
print(f"- Pages not found in SEBI database: {(~pages_df['sebi_exists']).sum()}")
print(f"- Average ads per page: {pages_df['total_ads'].mean():.2f}")
print(f"- Average active days (inactive ads only): {pages_df['avg_active_days'].mean():.2f}")

# Show sample of results
print(f"\nSample of results:")
print(pages_df.head(10).to_string())

# Show pages that exist in SEBI database
sebi_pages = pages_df[pages_df['sebi_exists'] == True]
if len(sebi_pages) > 0:
    print(f"\nPages found in SEBI database:")
    print(sebi_pages[['Page Name', 'total_ads', 'sebi_exists']].to_string())
else:
    print(f"\nNo pages were found in SEBI database.")

print("\nAnalysis complete!")