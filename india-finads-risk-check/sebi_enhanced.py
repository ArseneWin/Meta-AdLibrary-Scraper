import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
import numpy as np
import ast
import time
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
import re
import urllib.parse
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedSEBIChecker:
    """Enhanced SEBI registration checker with comprehensive analysis"""
    
    def __init__(self):
        self.sebi_headers = {
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
        
    async def search_page_in_sebi_async(self, session, page_name, headers):
        """Search a page name in SEBI database and return detailed results (async version)"""
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
                
                # Extract detailed information if found
                results = []
                for table in card_tables:
                    # Try to extract registration details
                    try:
                        rows = table.find_all('tr')
                        for row in rows:
                            cells = row.find_all('td')
                            if len(cells) >= 3:  # Assuming at least 3 columns
                                entity_info = {
                                    'name': cells[0].get_text(strip=True) if len(cells) > 0 else '',
                                    'registration_number': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                                    'category': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                                    'status': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                                    'registration_date': cells[4].get_text(strip=True) if len(cells) > 4 else ''
                                }
                                results.append(entity_info)
                    except Exception as e:
                        logger.warning(f"Error parsing SEBI result for {page_name}: {e}")
                
                return len(card_tables) > 0, results
                
        except Exception as e:
            logger.error(f"Error searching for {page_name}: {e}")
            return False, []

    def search_page_in_sebi(self, page_name, headers):
        """Search a page name in SEBI database and return detailed results (sync version)"""
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
            
            # Extract detailed information if found
            results = []
            for table in card_tables:
                # Try to extract registration details
                try:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 3:  # Assuming at least 3 columns
                            entity_info = {
                                'name': cells[0].get_text(strip=True) if len(cells) > 0 else '',
                                'registration_number': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                                'category': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                                'status': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                                'registration_date': cells[4].get_text(strip=True) if len(cells) > 4 else ''
                            }
                            results.append(entity_info)
                except Exception as e:
                    logger.warning(f"Error parsing SEBI result for {page_name}: {e}")
            
            return len(card_tables) > 0, results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching for {page_name}: {e}")
            return False, []

    async def search_all_pages_async(self, pages_df, headers):
        """Search all pages in SEBI database asynchronously with detailed results"""
        logger.info(f"Starting async search for {len(pages_df)} pages...")
        
        # Create a semaphore to limit concurrent requests (be respectful to the API)
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
        
        async def search_with_semaphore(session, page_name, page_idx):
            async with semaphore:
                logger.info(f"Searching {page_idx+1}/{len(pages_df)}: {page_name}")
                found, details = await self.search_page_in_sebi_async(session, page_name, headers)
                # Small delay to be respectful to the API
                await asyncio.sleep(0.1)
                return found, details
        
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
                    logger.error(f"Exception for page {i}: {result}")
                    processed_results.append((False, []))
                else:
                    processed_results.append(result)
            
            return processed_results

class PageAnalyzer:
    """Analyzes page data for risk patterns and suspicious behavior"""
    
    @staticmethod
    def extract_domain_from_page_link(page_link: str) -> str:
        """Extract domain from page link"""
        if not page_link:
            return ""
        try:
            parsed = urllib.parse.urlparse(page_link)
            return parsed.netloc.lower().replace('www.', '')
        except:
            return ""
    
    @staticmethod
    def analyze_page_name_patterns(page_name: str) -> Dict[str, Any]:
        """Analyze page name for suspicious patterns"""
        if not page_name:
            return {}
        
        page_name_lower = page_name.lower()
        
        analysis = {
            'has_numbers': bool(re.search(r'\d', page_name)),
            'has_special_chars': bool(re.search(r'[^a-zA-Z0-9\s]', page_name)),
            'length': len(page_name),
            'word_count': len(page_name.split()),
            'contains_investment_keywords': any(keyword in page_name_lower for keyword in [
                'investment', 'trading', 'forex', 'crypto', 'profit', 'earn', 'money',
                'capital', 'finance', 'wealth', 'stock', 'fund', 'portfolio'
            ]),
            'contains_urgency_keywords': any(keyword in page_name_lower for keyword in [
                'quick', 'fast', 'instant', 'rapid', 'immediate', 'urgent', 'now'
            ]),
            'contains_guarantee_keywords': any(keyword in page_name_lower for keyword in [
                'guaranteed', 'sure', 'certain', 'risk-free', 'safe', '100%'
            ]),
            'all_caps_ratio': sum(1 for c in page_name if c.isupper()) / len(page_name) if page_name else 0
        }
        
        return analysis
    
    @staticmethod
    def calculate_page_risk_score(page_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive risk score for a page"""
        risk_score = 0
        risk_factors = []
        
        # Analyze page name
        page_name_analysis = PageAnalyzer.analyze_page_name_patterns(page_data.get('Page Name', ''))
        
        # Risk factors based on page name
        if page_name_analysis.get('contains_investment_keywords'):
            risk_score += 2
            risk_factors.append("Investment-related page name")
        
        if page_name_analysis.get('contains_urgency_keywords'):
            risk_score += 3
            risk_factors.append("Urgency keywords in page name")
        
        if page_name_analysis.get('contains_guarantee_keywords'):
            risk_score += 4
            risk_factors.append("Guarantee keywords in page name")
        
        if page_name_analysis.get('all_caps_ratio', 0) > 0.5:
            risk_score += 2
            risk_factors.append("Excessive capitalization in page name")
        
        if page_name_analysis.get('has_numbers') and page_name_analysis.get('word_count', 0) < 3:
            risk_score += 1
            risk_factors.append("Short page name with numbers")
        
        # Risk factors based on advertising behavior
        total_ads = page_data.get('total_ads', 0)
        active_ads = page_data.get('active_ads', 0)
        inactive_ads = page_data.get('inactive_ads', 0)
        
        if total_ads > 20:
            risk_score += 2
            risk_factors.append("High number of ads")
        
        if active_ads > inactive_ads and total_ads > 5:
            risk_score += 1
            risk_factors.append("More active than inactive ads")
        
        avg_active_days = page_data.get('avg_active_days', 0)
        if avg_active_days and avg_active_days < 7:
            risk_score += 3
            risk_factors.append("Very short average campaign duration")
        elif avg_active_days and avg_active_days > 90:
            risk_score += 1
            risk_factors.append("Very long average campaign duration")
        
        # Platform diversity risk
        platform_columns = [col for col in page_data.keys() if col.endswith('_ad_count')]
        active_platforms = sum(1 for col in platform_columns if page_data.get(col, 0) > 0)
        
        if active_platforms > 2:
            risk_score += 1
            risk_factors.append("Multi-platform advertising")
        
        # SEBI registration status
        sebi_exists = page_data.get('sebi_exists', False)
        if not sebi_exists:
            risk_score += 5
            risk_factors.append("Not registered with SEBI")
        
        # Domain analysis
        page_link = page_data.get('PageLink', '')
        domain = PageAnalyzer.extract_domain_from_page_link(page_link)
        
        if not domain:
            risk_score += 2
            risk_factors.append("No valid page link")
        elif 'facebook.com' not in domain and 'instagram.com' not in domain:
            risk_score += 1
            risk_factors.append("Non-standard social media platform")
        
        # Determine overall risk level
        if risk_score >= 15:
            risk_level = 'CRITICAL'
        elif risk_score >= 10:
            risk_level = 'HIGH'
        elif risk_score >= 6:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'page_name_analysis': page_name_analysis,
            'domain': domain,
            'total_risk_factors': len(risk_factors)
        }

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

def load_and_analyze_data(csv_file: str) -> pd.DataFrame:
    """Load and perform initial analysis of the CSV data"""
    logger.info(f"Reading {csv_file}...")
    df = pd.read_csv(csv_file)
    
    logger.info(f"Original data shape: {df.shape}")
    logger.info(f"Columns: {df.columns.tolist()}")
    
    # Convert Total Active Days to numeric, handling NaN values
    if 'Total Active Days' in df.columns:
        df['Total Active Days'] = pd.to_numeric(df['Total Active Days'], errors='coerce')
    
    # Parse platforms column
    if 'Platforms' in df.columns:
        df['Platforms_List'] = df['Platforms'].apply(parse_platforms)
        
        # Create individual platform columns
        all_platforms = set()
        for platforms_list in df['Platforms_List']:
            all_platforms.update(platforms_list)
        
        logger.info(f"Found platforms: {sorted(all_platforms)}")
        
        # Create boolean columns for each platform
        for platform in all_platforms:
            df[f'{platform}_ads'] = df['Platforms_List'].apply(lambda x: platform in x)
    
    return df

def create_enhanced_page_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Create enhanced page-level summary with risk analysis"""
    logger.info("Creating enhanced page-level summary...")
    
    grouped_data = []
    
    for (page_name, page_link), group in df.groupby(['Page Name', 'PageLink']):
        row_data = {
            'Page Name': page_name,
            'PageLink': page_link,
            'total_ads': len(group),
            'active_ads': len(group[group['Status'] == 'Active']) if 'Status' in group.columns else 0,
            'inactive_ads': len(group[group['Status'] != 'Active']) if 'Status' in group.columns else 0
        }
        
        # Count ads per platform
        platform_columns = [col for col in group.columns if col.endswith('_ads')]
        for col in platform_columns:
            platform_name = col.replace('_ads', '')
            row_data[f'{platform_name}_ad_count'] = group[col].sum()
        
        # Calculate metrics based on available columns
        if 'Total Active Days' in group.columns:
            # Calculate average total active days (excluding active ads as requested)
            inactive_ads_with_days = group[(group['Status'] != 'Active') & (group['Total Active Days'].notna())]
            if len(inactive_ads_with_days) > 0:
                row_data['avg_active_days'] = inactive_ads_with_days['Total Active Days'].mean()
            else:
                row_data['avg_active_days'] = 0
        
        # Add spending analysis if available
        if 'Amount spent (INR)' in group.columns:
            # Count ads with spending data
            ads_with_spend = group[group['Amount spent (INR)'].notna() & (group['Amount spent (INR)'] != 'Undisclosed')]
            row_data['ads_with_spend_data'] = len(ads_with_spend)
            row_data['ads_spend_undisclosed'] = len(group[group['Amount spent (INR)'] == 'Undisclosed'])
        
        # Add risk indicators from ads
        if 'risk_risk_level' in group.columns:
            risk_counts = group['risk_risk_level'].value_counts().to_dict()
            row_data['high_risk_ads'] = risk_counts.get('HIGH', 0) + risk_counts.get('CRITICAL', 0)
            row_data['medium_risk_ads'] = risk_counts.get('MEDIUM', 0)
            row_data['low_risk_ads'] = risk_counts.get('LOW', 0)
            
            # Calculate page-level risk based on ad risks
            if row_data['high_risk_ads'] > row_data['total_ads'] * 0.7:
                row_data['page_ad_risk_level'] = 'HIGH'
            elif row_data['medium_risk_ads'] + row_data['high_risk_ads'] > row_data['total_ads'] * 0.5:
                row_data['page_ad_risk_level'] = 'MEDIUM'
            else:
                row_data['page_ad_risk_level'] = 'LOW'
        
        # Add keyword analysis
        if 'Keyword' in group.columns:
            unique_keywords = group['Keyword'].nunique()
            row_data['unique_keywords_used'] = unique_keywords
            row_data['keyword_diversity'] = unique_keywords / len(group) if len(group) > 0 else 0
        
        # Add date analysis
        if 'Start Date' in group.columns:
            valid_dates = group[group['Start Date'].notna() & (group['Start Date'] != '')]
            if len(valid_dates) > 0:
                try:
                    dates = pd.to_datetime(valid_dates['Start Date'], format='%d %b %Y', errors='coerce')
                    dates = dates.dropna()
                    if len(dates) > 0:
                        row_data['earliest_ad_date'] = dates.min().strftime('%Y-%m-%d')
                        row_data['latest_ad_date'] = dates.max().strftime('%Y-%m-%d')
                        row_data['campaign_span_days'] = (dates.max() - dates.min()).days
                except:
                    pass
        
        grouped_data.append(row_data)
    
    # Create the grouped dataframe
    pages_df = pd.DataFrame(grouped_data)
    logger.info(f"Created summary for {len(pages_df)} unique pages")
    
    return pages_df

async def enhanced_sebi_analysis(pages_df: pd.DataFrame) -> pd.DataFrame:
    """Perform enhanced SEBI analysis with detailed results"""
    logger.info("Starting enhanced SEBI analysis...")
    
    # Initialize SEBI checker
    sebi_checker = EnhancedSEBIChecker()
    
    # Search for each page using async calls for better performance
    start_time = time.time()
    sebi_results = await sebi_checker.search_all_pages_async(pages_df, sebi_checker.sebi_headers)
    end_time = time.time()
    
    # Process results
    pages_df['sebi_exists'] = [result[0] for result in sebi_results]
    pages_df['sebi_details'] = [result[1] for result in sebi_results]
    pages_df['sebi_matches_count'] = [len(result[1]) for result in sebi_results]
    
    logger.info(f"SEBI search completed in {end_time - start_time:.2f} seconds")
    logger.info(f"Average time per search: {(end_time - start_time) / len(pages_df):.3f} seconds")
    
    return pages_df

def perform_comprehensive_analysis(pages_df: pd.DataFrame) -> pd.DataFrame:
    """Perform comprehensive risk analysis on all pages"""
    logger.info("Performing comprehensive risk analysis...")
    
    # Add risk analysis for each page
    risk_analyses = []
    for _, row in pages_df.iterrows():
        risk_analysis = PageAnalyzer.calculate_page_risk_score(row.to_dict())
        risk_analyses.append(risk_analysis)
    
    # Add risk analysis columns
    for key in ['risk_score', 'risk_level', 'risk_factors', 'total_risk_factors', 'domain']:
        pages_df[key] = [analysis[key] for analysis in risk_analyses]
    
    # Add page name analysis
    page_name_analyses = [analysis['page_name_analysis'] for analysis in risk_analyses]
    for key in ['has_numbers', 'has_special_chars', 'length', 'word_count', 
                'contains_investment_keywords', 'contains_urgency_keywords', 
                'contains_guarantee_keywords', 'all_caps_ratio']:
        pages_df[f'page_name_{key}'] = [analysis.get(key, None) for analysis in page_name_analyses]
    
    return pages_df

def generate_detailed_report(pages_df: pd.DataFrame, output_filename: str):
    """Generate detailed analysis report"""
    logger.info("Generating detailed analysis report...")
    
    report = []
    report.append("=" * 80)
    report.append("ENHANCED INVESTMENT SCAM PAGE ANALYSIS REPORT")
    report.append("=" * 80)
    report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Total pages analyzed: {len(pages_df)}")
    report.append("")
    
    # SEBI Registration Analysis
    report.append("SEBI REGISTRATION ANALYSIS:")
    report.append("-" * 40)
    sebi_registered = pages_df['sebi_exists'].sum()
    sebi_not_registered = len(pages_df) - sebi_registered
    report.append(f"- Pages registered with SEBI: {sebi_registered} ({sebi_registered/len(pages_df)*100:.1f}%)")
    report.append(f"- Pages NOT registered with SEBI: {sebi_not_registered} ({sebi_not_registered/len(pages_df)*100:.1f}%)")
    
    if 'sebi_matches_count' in pages_df.columns:
        multi_matches = len(pages_df[pages_df['sebi_matches_count'] > 1])
        report.append(f"- Pages with multiple SEBI matches: {multi_matches}")
    
    report.append("")
    
    # Risk Level Analysis
    if 'risk_level' in pages_df.columns:
        report.append("RISK LEVEL DISTRIBUTION:")
        report.append("-" * 40)
        risk_summary = pages_df['risk_level'].value_counts()
        for level, count in risk_summary.items():
            report.append(f"- {level}: {count} pages ({count/len(pages_df)*100:.1f}%)")
        report.append("")
    
    # Platform Analysis
    platform_columns = [col for col in pages_df.columns if col.endswith('_ad_count')]
    if platform_columns:
        report.append("PLATFORM DISTRIBUTION:")
        report.append("-" * 40)
        for col in platform_columns:
            platform_name = col.replace('_ad_count', '')
            pages_with_platform = len(pages_df[pages_df[col] > 0])
            total_ads_on_platform = pages_df[col].sum()
            report.append(f"- {platform_name}: {pages_with_platform} pages, {total_ads_on_platform} total ads")
        report.append("")
    
    # High-Risk Pages
    if 'risk_level' in pages_df.columns:
        high_risk_pages = pages_df[pages_df['risk_level'].isin(['HIGH', 'CRITICAL'])]
        if len(high_risk_pages) > 0:
            report.append("HIGH-RISK PAGES (TOP 10):")
            report.append("-" * 40)
            top_high_risk = high_risk_pages.nlargest(10, 'risk_score')
            for _, page in top_high_risk.iterrows():
                report.append(f"- {page['Page Name']} (Risk Score: {page['risk_score']}, SEBI: {'Yes' if page['sebi_exists'] else 'No'})")
                if 'risk_factors' in page and page['risk_factors']:
                    factors = page['risk_factors'][:3]  # Show top 3 factors
                    report.append(f"  Factors: {', '.join(factors)}")
            report.append("")
    
    # Pages with most ads
    report.append("PAGES WITH MOST ADS (TOP 10):")
    report.append("-" * 40)
    top_advertisers = pages_df.nlargest(10, 'total_ads')
    for _, page in top_advertisers.iterrows():
        report.append(f"- {page['Page Name']}: {page['total_ads']} ads (SEBI: {'Yes' if page['sebi_exists'] else 'No'})")
    report.append("")
    
    # Domain Analysis
    if 'domain' in pages_df.columns:
        domain_counts = pages_df['domain'].value_counts()
        report.append("TOP DOMAINS:")
        report.append("-" * 40)
        for domain, count in domain_counts.head(10).items():
            if domain:
                report.append(f"- {domain}: {count} pages")
        report.append("")
    
    # Write report to file
    report_filename = output_filename.replace('.csv', '_report.txt')
    with open(report_filename, 'w') as f:
        f.write('\n'.join(report))
    
    logger.info(f"Detailed report saved to: {report_filename}")
    
    # Print summary to console
    print("\n".join(report[:50]))  # Print first 50 lines
    if len(report) > 50:
        print(f"\n... (full report saved to {report_filename})")

async def main_enhanced_sebi_analysis(csv_file: str = None):
    """Main function for enhanced SEBI analysis"""
    
    # Determine input file
    if csv_file:
        input_file = csv_file
    else:
        # Look for recent output files
        import glob
        csv_files = glob.glob('*investment_scam*.csv')
        if not csv_files:
            csv_files = glob.glob('*.csv')
        
        if not csv_files:
            logger.error("No CSV files found. Please specify a file or run the scraper first.")
            return
        
        # Use the most recent file
        input_file = max(csv_files, key=lambda x: time.ctime(time.path.getmtime(x)))
        logger.info(f"Using most recent file: {input_file}")
    
    try:
        # Load and analyze data
        df = load_and_analyze_data(input_file)
        
        # Create page-level summary
        pages_df = create_enhanced_page_summary(df)
        
        # Perform SEBI analysis
        pages_df = await enhanced_sebi_analysis(pages_df)
        
        # Perform comprehensive risk analysis
        pages_df = perform_comprehensive_analysis(pages_df)
        
        # Save enhanced results
        output_filename = f'enhanced_pages_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        pages_df.to_csv(output_filename, index=False)
        
        # Generate detailed report
        generate_detailed_report(pages_df, output_filename)
        
        logger.info(f"Enhanced analysis completed!")
        logger.info(f"Results saved to: {output_filename}")
        
        # Print quick summary
        print(f"\n" + "=" * 60)
        print("QUICK SUMMARY:")
        print(f"- Total pages analyzed: {len(pages_df)}")
        print(f"- SEBI registered: {pages_df['sebi_exists'].sum()}")
        print(f"- Not SEBI registered: {len(pages_df) - pages_df['sebi_exists'].sum()}")
        
        if 'risk_level' in pages_df.columns:
            risk_summary = pages_df['risk_level'].value_counts()
            print("Risk levels:")
            for level, count in risk_summary.items():
                print(f"  - {level}: {count}")
        
        print(f"- Detailed results: {output_filename}")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Error in enhanced SEBI analysis: {e}")
        raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced SEBI Registration Analysis')
    parser.add_argument('--input-file', type=str, help='Input CSV file to analyze')
    parser.add_argument('--output-dir', type=str, default='.', help='Output directory for results')
    
    args = parser.parse_args()
    
    try:
        asyncio.run(main_enhanced_sebi_analysis(args.input_file))
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
