"""
Main resume scraper orchestrator
Coordinates search, download, parse, and storage operations
"""
from typing import List, Dict, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .search_config import SearchConfig
from .google_search import GoogleSearchClient
from .resume_downloader import ResumeDownloader
from .resume_parser import ResumeParser
from services import resume_service, storage_service, llm_service
from models import ResumeCreate
import os
import re


class ResumeScraper:
    """Main scraper class that orchestrates the entire scraping process"""

    def __init__(
        self,
        search_config: Optional[SearchConfig] = None,
        download_dir: str = "./downloads"
    ):
        """
        Initialize the scraper

        Args:
            search_config: SearchConfig instance (uses default if not provided)
            download_dir: Directory to save downloaded resumes
        """
        self.search_config = search_config or SearchConfig()
        self.search_client = GoogleSearchClient()
        self.downloader = ResumeDownloader(download_dir=download_dir)
        self.parser = ResumeParser()
        self.stats = {
            "queries_executed": 0,
            "results_found": 0,
            "files_downloaded": 0,
            "files_parsed": 0,
            "files_uploaded": 0,
            "resumes_saved": 0,
            "errors": 0,
        }
        self.stats_lock = threading.Lock()  # Thread-safe stats updates

    def run(self, max_queries: Optional[int] = None, skip_existing: bool = True):
        """
        Run the complete scraping process

        Args:
            max_queries: Maximum number of queries to execute (None = all)
            skip_existing: Skip downloading/parsing if resume with same email exists
        """
        print("=" * 60)
        print("Starting Resume Scraper")
        print("=" * 60)

        # Build search queries
        queries = self.search_config.build_search_queries()

        if max_queries:
            queries = queries[:max_queries]

        print(f"\nGenerated {len(queries)} search queries")
        print(f"Results per query: {self.search_config.results_per_query}")

        # Execute searches
        print("\n" + "=" * 60)
        print("Phase 1: Searching for resumes")
        print("=" * 60)

        search_results = self.search_client.search_multiple_queries(
            queries=queries,
            results_per_query=self.search_config.results_per_query,
            delay_between_queries=1.0
        )

        self.stats["queries_executed"] = len(search_results)

        # Collect all unique URLs
        all_urls = set()
        url_metadata = {}  # Store metadata for each URL

        for query_str, result_data in search_results.items():
            results = result_data["results"]
            metadata = result_data["metadata"]

            for result in results:
                url = result.get("link")
                if url and url not in all_urls:
                    all_urls.add(url)
                    url_metadata[url] = {
                        "query": query_str,
                        "job_title": metadata.get("job_title"),
                        "seniority": metadata.get("seniority"),
                        "company": metadata.get("company"),
                        "title": result.get("title"),
                        "snippet": result.get("snippet"),
                    }

        self.stats["results_found"] = len(all_urls)
        print(f"\n✓ Found {len(all_urls)} unique resume URLs")

        # Download resumes (in parallel)
        print("\n" + "=" * 60)
        print("Phase 2: Downloading resumes (10 parallel workers)")
        print("=" * 60)

        downloaded_files = []

        def download_file(url_data):
            url, metadata = url_data
            result = self.downloader.download(url)
            if result:
                file_path, file_type = result
                return {
                    "file_path": file_path,
                    "file_type": file_type,
                    "url": url,
                    "metadata": metadata
                }
            return None

        # Parallel download with 10 workers
        with ThreadPoolExecutor(max_workers=10) as executor:
            url_items = [(url, url_metadata[url]) for url in all_urls]
            futures = {executor.submit(download_file, item): item for item in url_items}

            completed = 0
            for future in as_completed(futures):
                completed += 1
                url, _ = futures[future]
                print(f"[{completed}/{len(all_urls)}] Downloaded: {url}")

                result = future.result()
                if result:
                    downloaded_files.append(result)
                    self.stats["files_downloaded"] += 1

        print(f"\n✓ Downloaded {len(downloaded_files)} files")

        # Parse and save resumes (in parallel)
        print("\n" + "=" * 60)
        print("Phase 3: Parsing and saving to database (10 parallel workers)")
        print("=" * 60)

        def process_file(file_info):
            """Process a single resume file"""
            try:
                # Parse the file
                parsed_data = self.parser.parse_file(
                    file_info["file_path"],
                    file_info["file_type"]
                )

                if not parsed_data:
                    print(f"  ✗ Failed to parse file: {file_info['file_path']}")
                    with self.stats_lock:
                        self.stats["errors"] += 1
                    return

                with self.stats_lock:
                    self.stats["files_parsed"] += 1

                # Check if resume already exists (by email)
                if skip_existing and parsed_data.get("email"):
                    existing = resume_service.get_resume_by_email(parsed_data["email"])
                    if existing:
                        print(f"  ⊘ Resume with email {parsed_data['email']} already exists, skipping")
                        return

                # Extract skills from raw text
                skills = self.parser.extract_skills(parsed_data["raw_text"])

                # Validate and clean email
                email = parsed_data.get("email")
                if email:
                    email = self._validate_email(email)

                # Use LLM to extract structured data
                print(f"  → Using LLM to parse: {file_info['file_path']}")
                llm_data = llm_service.parse_resume(parsed_data["raw_text"])

                if not llm_data:
                    print(f"  ⚠ LLM parsing failed, using basic data only")
                    llm_data = {}

                # Upload file to Supabase Storage
                print(f"  → Uploading to Supabase: {file_info['file_path']}")
                supabase_url = storage_service.upload_file(file_info["file_path"])

                if not supabase_url:
                    print(f"  ✗ Failed to upload to Supabase Storage")
                    with self.stats_lock:
                        self.stats["errors"] += 1
                    return

                with self.stats_lock:
                    self.stats["files_uploaded"] += 1

                # Create ResumeCreate object (use Supabase URL as file_url)
                # Merge LLM data with basic parsed data
                resume_data = ResumeCreate(
                    name=llm_data.get("name"),
                    email=email,
                    phone=parsed_data.get("phone"),
                    location=llm_data.get("location"),
                    title=file_info["metadata"].get("job_title"),
                    seniority=file_info["metadata"].get("seniority"),
                    company=file_info["metadata"].get("company"),
                    years_of_experience=llm_data.get("years_of_experience"),
                    experience=llm_data.get("experience", []),
                    education=llm_data.get("education", []),
                    projects=llm_data.get("projects", []),
                    skills=skills,  # Keep regex-extracted skills
                    certifications=llm_data.get("certifications", []),
                    file_url=supabase_url,  # Supabase Storage URL
                    file_name=parsed_data["file_name"],
                    file_type=parsed_data["file_type"],
                    search_query=file_info["metadata"]["query"],
                    source_url=file_info["url"],  # Original URL
                    raw_text=parsed_data["raw_text"]
                )

                # Save to database
                saved_resume = resume_service.create_resume(resume_data)

                if saved_resume:
                    print(f"  ✓ Saved to database (ID: {saved_resume.id})")
                    with self.stats_lock:
                        self.stats["resumes_saved"] += 1
                else:
                    print(f"  ✗ Failed to save to database")
                    with self.stats_lock:
                        self.stats["errors"] += 1

            except Exception as e:
                print(f"  ✗ Error processing file: {e}")
                with self.stats_lock:
                    self.stats["errors"] += 1
            finally:
                # Always delete local file after processing (success or failure)
                try:
                    if os.path.exists(file_info["file_path"]):
                        os.remove(file_info["file_path"])
                        print(f"  ✓ Cleaned up: {file_info['file_path']}")
                except Exception as e:
                    print(f"  ⚠ Could not delete local file: {e}")

        # Process files in parallel with 10 workers
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(process_file, file): file for file in downloaded_files}

            completed = 0
            for future in as_completed(futures):
                completed += 1
                print(f"\n[{completed}/{len(downloaded_files)}] Processing completed")
                future.result()  # This will raise any exceptions that occurred

        # Print summary
        self._print_summary()

    def _validate_email(self, email: str) -> Optional[str]:
        """
        Validate and clean email address

        Args:
            email: Email string to validate

        Returns:
            Cleaned email if valid, None otherwise
        """
        if not email:
            return None

        # Basic email validation pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        # Strip whitespace
        email = email.strip()

        # Check if it matches the pattern
        if re.match(email_pattern, email):
            return email.lower()  # Return lowercase for consistency

        return None

    def _print_summary(self):
        """Print scraping statistics"""
        print("\n" + "=" * 60)
        print("SCRAPING COMPLETE - Summary")
        print("=" * 60)
        print(f"Queries executed:     {self.stats['queries_executed']}")
        print(f"Results found:        {self.stats['results_found']}")
        print(f"Files downloaded:     {self.stats['files_downloaded']}")
        print(f"Files parsed:         {self.stats['files_parsed']}")
        print(f"Files uploaded:       {self.stats['files_uploaded']}")
        print(f"Resumes saved to DB:  {self.stats['resumes_saved']}")
        print(f"Errors:               {self.stats['errors']}")
        print("=" * 60)


def run_scraper(
    job_titles: Optional[List[str]] = None,
    seniority_levels: Optional[List[str]] = None,
    companies: Optional[List[str]] = None,
    max_queries: Optional[int] = None,
    download_dir: str = "./downloads"
):
    """
    Convenience function to run the scraper with custom configuration

    Args:
        job_titles: List of job titles to search for
        seniority_levels: List of seniority levels
        companies: List of companies to filter by
        max_queries: Maximum number of queries to execute
        download_dir: Directory to save downloads

    Example:
        run_scraper(
            job_titles=["software engineer", "data scientist"],
            seniority_levels=["senior", "staff"],
            companies=["Google", "Amazon"],
            max_queries=5
        )
    """
    # Create search config
    config = SearchConfig()

    if job_titles:
        config.job_titles = job_titles
    if seniority_levels:
        config.seniority_levels = seniority_levels
    if companies:
        config.companies = companies

    # Create and run scraper
    scraper = ResumeScraper(search_config=config, download_dir=download_dir)
    scraper.run(max_queries=max_queries)


# Example usage
if __name__ == "__main__":
    # Run with default config
    run_scraper(max_queries=2)  # Start small for testing
