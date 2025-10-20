#!/usr/bin/env python3
"""
Manual script to run the resume scraper
Customize the parameters below and run: python run_scraper.py
"""

from scraper import ResumeScraper, SearchConfig

if __name__ == "__main__":
    # ========================================
    # CUSTOMIZE YOUR SEARCH HERE
    # ========================================

    config = SearchConfig(
        job_titles=[
            "software engineer",
            "software developer",
        ],
        seniority_levels=[
            "intern",
        ],
        file_types=["pdf"],  # PDF only - no wasted DOCX queries!
        companies=[
            "Google",
            "Two Sigma",
            "Blackstone",
            "Nvida",
            "Microsoft",
            "Atlassian",
            "Apple",
            "Uber",
            "OpenAi",
            "Lyft",
            "Amazon",
            "Netflix",
            "JPMorgan Chase",
        ],
    )

    scraper = ResumeScraper(search_config=config, download_dir="./downloads")
    scraper.run(max_queries=10)  # 10 queries = 5 companies (2 queries each)

    # Option 2: Use custom SearchConfig for more control
    # from scraper import ResumeScraper
    #
    # config = SearchConfig(
    #     job_titles=["machine learning engineer"],
    #     seniority_levels=["senior", "staff"],
    #     companies=["Google", "Meta"],
    #     file_types=["pdf"],  # Only search PDFs
    #     results_per_query=10,
    #     exclude_terms=["template", "example", "sample"]
    # )
    #
    # scraper = ResumeScraper(search_config=config, download_dir="./downloads")
    # scraper.run(max_queries=10)
