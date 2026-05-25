import json
import os
import hashlib
from datetime import datetime
import pandas as pd
from typing import Dict, List, Any, Optional
import time

class ProgressTracker:
    """Handles progressive saving and resuming of ad scraping progress"""
    
    def __init__(self, progress_file: str = "scraping_progress.json"):
        self.progress_file = progress_file
        self.progress_data = self.load_progress()
        
    def load_progress(self) -> Dict[str, Any]:
        """Load existing progress from file"""
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {
            "completed_searches": [],
            "failed_searches": [],
            "last_update": None,
            "total_ads_found": 0,
            "session_start": datetime.now().isoformat()
        }
    
    def save_progress(self):
        """Save current progress to file"""
        self.progress_data["last_update"] = datetime.now().isoformat()
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress_data, f, indent=2)
    
    def is_search_completed(self, ad_type: str, keyword: str) -> bool:
        """Check if a specific search has been completed"""
        search_key = f"{ad_type}|{keyword}"
        return search_key in self.progress_data["completed_searches"]
    
    def mark_search_completed(self, ad_type: str, keyword: str, ads_found: int):
        """Mark a search as completed"""
        search_key = f"{ad_type}|{keyword}"
        if search_key not in self.progress_data["completed_searches"]:
            self.progress_data["completed_searches"].append(search_key)
        self.progress_data["total_ads_found"] += ads_found
        self.save_progress()
    
    def mark_search_failed(self, ad_type: str, keyword: str, error: str):
        """Mark a search as failed"""
        search_key = f"{ad_type}|{keyword}"
        self.progress_data["failed_searches"].append({
            "search": search_key,
            "error": str(error),
            "timestamp": datetime.now().isoformat()
        })
        self.save_progress()
    
    def get_remaining_searches(self, all_searches: List[tuple]) -> List[tuple]:
        """Get list of searches that haven't been completed yet"""
        remaining = []
        for ad_type, keyword in all_searches:
            if not self.is_search_completed(ad_type, keyword):
                remaining.append((ad_type, keyword))
        return remaining
    
    def reset_progress(self):
        """Reset all progress (start fresh)"""
        if os.path.exists(self.progress_file):
            os.remove(self.progress_file)
        self.progress_data = {
            "completed_searches": [],
            "failed_searches": [],
            "last_update": None,
            "total_ads_found": 0,
            "session_start": datetime.now().isoformat()
        }

class AdDeduplicator:
    """Handles deduplication of ads based on various criteria"""
    
    @staticmethod
    def generate_ad_hash(ad_data: Dict[str, Any]) -> str:
        """Generate a unique hash for an ad based on key attributes"""
        # Use Library ID as primary identifier
        if ad_data.get('Library ID'):
            return f"lib_{ad_data['Library ID']}"
        
        # Fallback to content-based hash
        content_parts = [
            ad_data.get('Page Name', ''),
            ad_data.get('FullText', '')[:100],  # First 100 chars
            ad_data.get('Start Date', ''),
            ad_data.get('PageLink', '')
        ]
        content_string = '|'.join(str(part) for part in content_parts)
        return hashlib.md5(content_string.encode()).hexdigest()
    
    @staticmethod
    def deduplicate_ads(ads_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate ads from the list"""
        seen_hashes = set()
        deduplicated = []
        duplicates_count = 0
        
        for ad in ads_list:
            ad_hash = AdDeduplicator.generate_ad_hash(ad)
            
            if ad_hash not in seen_hashes:
                seen_hashes.add(ad_hash)
                ad['ad_hash'] = ad_hash
                deduplicated.append(ad)
            else:
                duplicates_count += 1
        
        print(f"Removed {duplicates_count} duplicate ads. {len(deduplicated)} unique ads remaining.")
        return deduplicated

class IncrementalDataSaver:
    """Handles incremental saving of scraped data"""
    
    def __init__(self, base_dir: str = "scraped_data"):
        self.base_dir = base_dir
        self.ensure_directory_exists()
    
    def ensure_directory_exists(self):
        """Create the base directory if it doesn't exist"""
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
    
    def save_ads_incrementally(self, ads_data: List[Dict[str, Any]], ad_type: str, keyword: str):
        """Save ads data incrementally to prevent data loss"""
        if not ads_data:
            return
        
        # Create filename based on ad type and keyword
        safe_ad_type = "".join(c for c in ad_type if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_ad_type}_{safe_keyword}_{timestamp}.csv"
        filepath = os.path.join(self.base_dir, filename)
        
        # Save to CSV
        df = pd.DataFrame(ads_data)
        df.to_csv(filepath, index=False)
        print(f"Saved {len(ads_data)} ads to {filepath}")
        
        # Also append to a master file for this ad type
        master_filename = f"{safe_ad_type}_master.csv"
        master_filepath = os.path.join(self.base_dir, master_filename)
        
        if os.path.exists(master_filepath):
            # Append to existing file
            df.to_csv(master_filepath, mode='a', header=False, index=False)
        else:
            # Create new file with headers
            df.to_csv(master_filepath, index=False)
    
    def load_all_saved_data(self) -> pd.DataFrame:
        """Load all previously saved data into a single DataFrame"""
        all_data = []
        
        for filename in os.listdir(self.base_dir):
            if filename.endswith('.csv') and not filename.endswith('_master.csv'):
                filepath = os.path.join(self.base_dir, filename)
                try:
                    df = pd.read_csv(filepath)
                    all_data.append(df)
                    print(f"Loaded {len(df)} ads from {filename}")
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            print(f"Total loaded ads: {len(combined_df)}")
            return combined_df
        else:
            print("No saved data found.")
            return pd.DataFrame()
    
    def get_latest_master_file(self, ad_type: str) -> Optional[str]:
        """Get the path to the latest master file for an ad type"""
        safe_ad_type = "".join(c for c in ad_type if c.isalnum() or c in (' ', '-', '_')).rstrip()
        master_filename = f"{safe_ad_type}_master.csv"
        master_filepath = os.path.join(self.base_dir, master_filename)
        
        if os.path.exists(master_filepath):
            return master_filepath
        return None

class RiskAnalyzer:
    """Analyzes ads for risk indicators and suspicious patterns"""
    
    # Risk indicators categorized by severity
    HIGH_RISK_KEYWORDS = [
        'guaranteed', 'risk-free', 'no risk', 'instant profit', 'quick money',
        'double your money', 'triple your investment', '100% returns',
        'zero loss', 'sure shot', 'confirmed profit', 'government scheme',
        'limited time offer', 'hurry up', 'last chance', 'exclusive offer'
    ]
    
    MEDIUM_RISK_KEYWORDS = [
        'high returns', 'passive income', 'easy money', 'work from home',
        'part time income', 'side income', 'extra income', 'bonus income',
        'referral income', 'join now', 'register now', 'sign up bonus',
        'free trial', 'demo account', 'no investment', 'small investment'
    ]
    
    CONTACT_RISK_PATTERNS = [
        r'telegram\.me', r't\.me', r'whatsapp', r'call.*\d{10}',
        r'contact.*\d{10}', r'dm for details', r'message for info',
        r'click link', r'register.*link'
    ]
    
    @staticmethod
    def calculate_risk_score(ad_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive risk score for an ad"""
        risk_analysis = {
            'risk_score': 0,
            'risk_level': 'LOW',
            'risk_factors': [],
            'high_risk_keywords_found': [],
            'medium_risk_keywords_found': [],
            'contact_patterns_found': [],
            'platform_risk_factor': 0,
            'duration_risk_factor': 0,
            'spend_risk_factor': 0
        }
        
        full_text = str(ad_data.get('FullText', '')).lower()
        page_name = str(ad_data.get('Page Name', '')).lower()
        combined_text = f"{full_text} {page_name}"
        
        # Check for high-risk keywords
        for keyword in RiskAnalyzer.HIGH_RISK_KEYWORDS:
            if keyword.lower() in combined_text:
                risk_analysis['risk_score'] += 3
                risk_analysis['high_risk_keywords_found'].append(keyword)
                risk_analysis['risk_factors'].append(f"High-risk keyword: {keyword}")
        
        # Check for medium-risk keywords
        for keyword in RiskAnalyzer.MEDIUM_RISK_KEYWORDS:
            if keyword.lower() in combined_text:
                risk_analysis['risk_score'] += 1
                risk_analysis['medium_risk_keywords_found'].append(keyword)
                risk_analysis['risk_factors'].append(f"Medium-risk keyword: {keyword}")
        
        # Check for contact patterns
        import re
        for pattern in RiskAnalyzer.CONTACT_RISK_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                risk_analysis['risk_score'] += 2
                risk_analysis['contact_patterns_found'].append(pattern)
                risk_analysis['risk_factors'].append(f"Suspicious contact pattern: {pattern}")
        
        # Platform-based risk assessment
        platforms = ad_data.get('Platforms', [])
        if isinstance(platforms, str):
            try:
                platforms = eval(platforms)
            except:
                platforms = [platforms]
        
        if 'Facebook' in platforms and 'Instagram' in platforms:
            risk_analysis['platform_risk_factor'] = 1
            risk_analysis['risk_score'] += 1
            risk_analysis['risk_factors'].append("Multi-platform presence")
        
        # Duration-based risk (very short or very long campaigns can be suspicious)
        total_days = ad_data.get('Total Active Days')
        if total_days:
            try:
                days = float(total_days)
                if days < 3:  # Very short campaigns
                    risk_analysis['duration_risk_factor'] = 2
                    risk_analysis['risk_score'] += 2
                    risk_analysis['risk_factors'].append("Very short campaign duration")
                elif days > 90:  # Very long campaigns
                    risk_analysis['duration_risk_factor'] = 1
                    risk_analysis['risk_score'] += 1
                    risk_analysis['risk_factors'].append("Very long campaign duration")
            except:
                pass
        
        # Spending pattern analysis
        amount_spent = ad_data.get('Amount spent (INR)', '')
        if amount_spent and amount_spent != 'Undisclosed':
            try:
                # Extract numeric value from spending range
                import re
                numbers = re.findall(r'[\d,]+', str(amount_spent))
                if numbers:
                    # Take the higher end of the range if available
                    spend_value = int(numbers[-1].replace(',', ''))
                    if spend_value > 100000:  # High spending
                        risk_analysis['spend_risk_factor'] = 1
                        risk_analysis['risk_score'] += 1
                        risk_analysis['risk_factors'].append("High advertising spend")
                    elif spend_value < 1000:  # Very low spending
                        risk_analysis['spend_risk_factor'] = 2
                        risk_analysis['risk_score'] += 2
                        risk_analysis['risk_factors'].append("Very low advertising spend")
            except:
                pass
        
        # Determine overall risk level
        if risk_analysis['risk_score'] >= 8:
            risk_analysis['risk_level'] = 'CRITICAL'
        elif risk_analysis['risk_score'] >= 5:
            risk_analysis['risk_level'] = 'HIGH'
        elif risk_analysis['risk_score'] >= 3:
            risk_analysis['risk_level'] = 'MEDIUM'
        else:
            risk_analysis['risk_level'] = 'LOW'
        
        return risk_analysis
    
    @staticmethod
    def add_risk_analysis_to_ads(ads_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add risk analysis to all ads in the list"""
        print("Performing risk analysis on ads...")
        
        for ad in ads_list:
            risk_analysis = RiskAnalyzer.calculate_risk_score(ad)
            
            # Add risk analysis fields to the ad
            for key, value in risk_analysis.items():
                ad[f'risk_{key}'] = value
        
        # Print risk analysis summary
        risk_levels = {}
        for ad in ads_list:
            level = ad.get('risk_risk_level', 'UNKNOWN')
            risk_levels[level] = risk_levels.get(level, 0) + 1
        
        print("Risk Analysis Summary:")
        for level, count in sorted(risk_levels.items()):
            print(f"  {level}: {count} ads")
        
        return ads_list

# Utility functions for backward compatibility
def save_incremental_data(ads_data: List[Dict[str, Any]], ad_type: str, keyword: str):
    """Convenience function for incremental saving"""
    saver = IncrementalDataSaver()
    saver.save_ads_incrementally(ads_data, ad_type, keyword)

def load_all_data() -> pd.DataFrame:
    """Convenience function to load all saved data"""
    saver = IncrementalDataSaver()
    return saver.load_all_saved_data()
