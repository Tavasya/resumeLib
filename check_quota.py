#!/usr/bin/env python3
"""
Check your Google Custom Search API quota usage
"""
print("To check your actual API quota usage:")
print("=" * 60)
print("\n1. Go to: https://console.cloud.google.com/apis/api/customsearch.googleapis.com/quotas")
print("\n2. Look for 'Queries per day' under the Custom Search JSON API")
print("\n3. It will show: [current usage] / 100")
print("\n" + "=" * 60)
print("\nFree Tier Limits:")
print("  • 100 queries per day")
print("  • Max 10 results per query")
print("  • Resets at midnight Pacific Time (PT)")
print("\n" + "=" * 60)
print("\nTips to conserve quota:")
print("  • Reduce max_queries in run_scraper.py")
print("  • Reduce results_per_query (default is 10)")
print("  • Remove seniority levels or file types you don't need")
print("=" * 60)
