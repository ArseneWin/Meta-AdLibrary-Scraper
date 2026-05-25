#!/usr/bin/env python3
"""
Demo script for Enhanced Investment Scam Detection System
This script demonstrates the key improvements and features.
"""

import json
import pandas as pd
from datetime import datetime
import os
import sys

def demo_enhanced_keywords():
    """Demonstrate the enhanced keyword system"""
    print("🔍 ENHANCED KEYWORDS DEMONSTRATION")
    print("=" * 50)
    
    # Load enhanced keywords
    with open('enhanced_keywords.json', 'r') as f:
        enhanced_keywords = json.load(f)
    
    # Load original keywords for comparison
    with open('keywords.json', 'r') as f:
        original_keywords = json.load(f)
    
    print(f"Original Keywords: {sum(len(v) for v in original_keywords.values())} total")
    print(f"Enhanced Keywords: {sum(len(v) for v in enhanced_keywords.values())} total")
    print(f"Improvement: {sum(len(v) for v in enhanced_keywords.values()) / sum(len(v) for v in original_keywords.values()):.1f}x more keywords")
    
    print("\nKeyword Categories:")
    for category, keywords in enhanced_keywords.items():
        print(f"  📂 {category}: {len(keywords)} keywords")
        print(f"     Examples: {', '.join(keywords[:3])}...")
    
    print("\n" + "=" * 50 + "\n")

def demo_risk_analysis():
    """Demonstrate the risk analysis system"""
    print("⚠️  RISK ANALYSIS DEMONSTRATION")
    print("=" * 50)
    
    # Import risk analyzer
    from data_utils import RiskAnalyzer
    
    # Sample ad data for demonstration
    sample_ads = [
        {
            "Page Name": "QuickProfit Investment",
            "FullText": "Guaranteed 100% returns! Risk-free investment! Join our Telegram for instant profits. Limited time offer!",
            "Total Active Days": 3,
            "Amount spent (INR)": "₹50,000 - ₹1,00,000",
            "Platforms": ["Facebook", "Instagram"]
        },
        {
            "Page Name": "ABC Financial Services",
            "FullText": "Professional investment advisory services. Registered with SEBI. Long-term wealth creation.",
            "Total Active Days": 45,
            "Amount spent (INR)": "₹5,00,000 - ₹10,00,000",
            "Platforms": ["Facebook"]
        }
    ]
    
    print("Analyzing sample ads for risk indicators...\n")
    
    for i, ad in enumerate(sample_ads, 1):
        risk_analysis = RiskAnalyzer.calculate_risk_score(ad)
        
        print(f"Ad {i}: {ad['Page Name']}")
        print(f"  Risk Level: {risk_analysis['risk_level']}")
        print(f"  Risk Score: {risk_analysis['risk_score']}/20")
        print(f"  Risk Factors: {len(risk_analysis['risk_factors'])}")
        
        if risk_analysis['risk_factors']:
            print("  Top Risk Factors:")
            for factor in risk_analysis['risk_factors'][:3]:
                print(f"    - {factor}")
        print()
    
    print("=" * 50 + "\n")

def demo_progressive_saving():
    """Demonstrate the progressive saving system"""
    print("💾 PROGRESSIVE SAVING DEMONSTRATION")
    print("=" * 50)
    
    from data_utils import ProgressTracker, IncrementalDataSaver
    
    # Initialize progress tracker
    tracker = ProgressTracker()
    saver = IncrementalDataSaver()
    
    print("Progress Tracking Features:")
    print("  ✅ Automatic progress file creation")
    print("  ✅ Resume capability after interruption")
    print("  ✅ Failed search tracking")
    print("  ✅ Incremental data saving every 10 scrolls")
    
    # Show current progress if exists
    if os.path.exists("scraping_progress.json"):
        with open("scraping_progress.json", 'r') as f:
            progress = json.load(f)
        
        print(f"\nCurrent Progress Status:")
        print(f"  - Completed searches: {len(progress.get('completed_searches', []))}")
        print(f"  - Failed searches: {len(progress.get('failed_searches', []))}")
        print(f"  - Total ads found: {progress.get('total_ads_found', 0)}")
        if progress.get('last_update'):
            print(f"  - Last update: {progress['last_update']}")
    else:
        print("\nNo previous progress found (fresh start)")
    
    print("\nData Saving Structure:")
    if os.path.exists("scraped_data"):
        files = os.listdir("scraped_data")
        print(f"  - Incremental saves: {len([f for f in files if not f.endswith('_master.csv')])} files")
        print(f"  - Master files: {len([f for f in files if f.endswith('_master.csv')])} files")
    else:
        print("  - No saved data found")
    
    print("=" * 50 + "\n")

def demo_deduplication():
    """Demonstrate the deduplication system"""
    print("🔄 DEDUPLICATION DEMONSTRATION")
    print("=" * 50)
    
    from data_utils import AdDeduplicator
    
    # Sample duplicate ads
    sample_ads = [
        {"Library ID": "123456", "Page Name": "Test Page", "FullText": "Sample ad content"},
        {"Library ID": "123456", "Page Name": "Test Page", "FullText": "Sample ad content"},  # Duplicate
        {"Library ID": "789012", "Page Name": "Another Page", "FullText": "Different content"},
        {"Library ID": "", "Page Name": "No ID Page", "FullText": "Same content here"},
        {"Library ID": "", "Page Name": "No ID Page", "FullText": "Same content here"},  # Content duplicate
    ]
    
    print(f"Original ads: {len(sample_ads)}")
    
    # Perform deduplication
    deduplicated = AdDeduplicator.deduplicate_ads(sample_ads)
    
    print(f"After deduplication: {len(deduplicated)}")
    print(f"Duplicates removed: {len(sample_ads) - len(deduplicated)}")
    
    print("\nDeduplication Methods:")
    print("  1. Library ID-based (primary)")
    print("  2. Content hash-based (fallback)")
    print("  3. Global deduplication across all searches")
    
    print("=" * 50 + "\n")

def demo_data_quality():
    """Demonstrate data quality improvements"""
    print("📊 DATA QUALITY IMPROVEMENTS")
    print("=" * 50)
    
    print("Enhanced Data Fields (50+ vs 15 original):")
    
    enhanced_fields = {
        "Basic Information": [
            "Library ID", "Page Name", "Status", "Ad URL", "Platforms",
            "Platform Count", "Is Multi Platform"
        ],
        "Temporal Analysis": [
            "Start Date", "End Date", "Total Active Days",
            "Days Since Start", "Days Since End"
        ],
        "Audience Metrics": [
            "Estimated Audience Size", "Audience Min", "Audience Max", "Audience Avg"
        ],
        "Financial Metrics": [
            "Amount Spent", "Spend Min", "Spend Max", "Spend Avg",
            "Daily Spend Avg", "Impressions", "CPM Estimated"
        ],
        "Risk Indicators": [
            "Contains Contact Info", "Contains Urgency Words",
            "Contains Guarantee Words", "Risk Score", "Risk Level"
        ],
        "Quality Metrics": [
            "Has Library ID", "Has Page Link", "Has Full Text",
            "Data Quality Score", "Full Text Length"
        ]
    }
    
    for category, fields in enhanced_fields.items():
        print(f"\n  📂 {category}:")
        for field in fields:
            print(f"     - {field}")
    
    print(f"\nTotal Enhanced Fields: {sum(len(fields) for fields in enhanced_fields.values())}")
    print("=" * 50 + "\n")

def demo_sebi_analysis():
    """Demonstrate SEBI analysis improvements"""
    print("🏛️  ENHANCED SEBI ANALYSIS")
    print("=" * 50)
    
    print("SEBI Analysis Features:")
    print("  ✅ Async batch processing for speed")
    print("  ✅ Detailed registration information extraction")
    print("  ✅ Multiple search strategies")
    print("  ✅ Page-level risk assessment")
    print("  ✅ Comprehensive reporting")
    
    print("\nPage-Level Analysis Includes:")
    analysis_features = [
        "Total ads per page",
        "Active vs inactive ad ratio",
        "Average campaign duration",
        "Platform distribution",
        "Keyword diversity",
        "Risk factor aggregation",
        "SEBI registration status",
        "Domain analysis",
        "Page name pattern analysis"
    ]
    
    for feature in analysis_features:
        print(f"  - {feature}")
    
    print("=" * 50 + "\n")

def show_usage_examples():
    """Show practical usage examples"""
    print("🚀 USAGE EXAMPLES")
    print("=" * 50)
    
    examples = [
        {
            "title": "Quick Start",
            "command": "python main_enhanced.py",
            "description": "Run with default settings and enhanced keywords"
        },
        {
            "title": "Resume Interrupted Session", 
            "command": "python main_enhanced.py --resume",
            "description": "Continue from where you left off"
        },
        {
            "title": "Target Specific Category",
            "command": "python main_enhanced.py --ad-type 'Cryptocurrency'",
            "description": "Search only cryptocurrency-related scams"
        },
        {
            "title": "Fast Testing",
            "command": "python main_enhanced.py --max-scrolls 10 --headless",
            "description": "Quick test with limited scrolling"
        },
        {
            "title": "Analyze SEBI Status",
            "command": "python sebi_enhanced.py",
            "description": "Check SEBI registration for all pages"
        }
    ]
    
    for example in examples:
        print(f"\n📝 {example['title']}:")
        print(f"   Command: {example['command']}")
        print(f"   Purpose: {example['description']}")
    
    print("=" * 50 + "\n")

def main():
    """Run the complete demonstration"""
    print("🎯 ENHANCED INVESTMENT SCAM DETECTION SYSTEM")
    print("📊 COMPREHENSIVE DEMONSTRATION")
    print("=" * 60)
    print(f"Demo run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")
    
    # Run all demonstrations
    demo_enhanced_keywords()
    demo_risk_analysis()
    demo_progressive_saving()
    demo_deduplication()
    demo_data_quality()
    demo_sebi_analysis()
    show_usage_examples()
    
    print("✅ DEMONSTRATION COMPLETE!")
    print("=" * 60)
    print("Ready to run the enhanced system:")
    print("  1. python main_enhanced.py     # Start scraping")
    print("  2. python sebi_enhanced.py     # Analyze SEBI status")
    print("=" * 60)

if __name__ == "__main__":
    main()
