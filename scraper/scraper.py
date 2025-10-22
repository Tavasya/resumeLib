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

                # Extract latest experience info (most recent job)
                latest_exp = self._extract_latest_experience(llm_data.get("experience", []))

                # Validate: Does latest experience have a similar job title?
                if not self._matches_search_criteria(latest_exp, file_info["metadata"]):
                    print(f"  ⊘ Job title doesn't match (searched for '{file_info['metadata']['job_title']}', got '{latest_exp.get('title')}'), skipping")
                    return

                # Create ResumeCreate object (use Supabase URL as file_url)
                # Use ACTUAL latest experience from resume, not search metadata
                resume_data = ResumeCreate(
                    name=llm_data.get("name"),
                    email=email,
                    phone=parsed_data.get("phone"),
                    location=llm_data.get("location"),
                    title=latest_exp.get("title"),  # Latest job title from resume
                    seniority=latest_exp.get("seniority"),  # Inferred from latest title
                    company=latest_exp.get("company"),  # Latest company from resume
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

    def _extract_latest_experience(self, experience: List[Dict]) -> Dict[str, Optional[str]]:
        """
        Extract latest/most recent experience from experience array

        Args:
            experience: List of experience dictionaries from LLM

        Returns:
            Dictionary with title, company, and seniority from latest job
        """
        if not experience or len(experience) == 0:
            return {"title": None, "company": None, "seniority": None}

        # Assume first experience is the most recent (LLM usually orders this way)
        latest = experience[0]

        title = latest.get("title")
        company = latest.get("company")

        # Infer seniority from job title
        seniority = self._infer_seniority(title) if title else None

        return {
            "title": title,
            "company": company,
            "seniority": seniority
        }

    def _matches_search_criteria(self, latest_exp: Dict[str, Optional[str]], search_metadata: Dict) -> bool:
        """
        Check if latest experience has a similar job title to what was searched
        (Ignores company and seniority - we save actual data from resume)

        Args:
            latest_exp: Latest experience data (title, company, seniority)
            search_metadata: Search query metadata (company, seniority, job_title)

        Returns:
            True if job title is similar, False otherwise
        """
        # If no latest experience title, skip it
        latest_title = latest_exp.get("title")
        if not latest_title:
            return False

        # Get searched job title
        search_job_title = search_metadata.get("job_title")
        if not search_job_title:
            # If no job title in search (shouldn't happen), accept it
            return True

        # Normalize for comparison
        latest_title_lower = latest_title.lower().strip()
        search_title_lower = search_job_title.lower().strip()

        # Extract key terms from both titles (remove common words)
        common_words = {"the", "a", "an", "and", "or", "of", "in", "at", "for", "to"}

        def extract_keywords(title):
            words = title.split()
            return {w for w in words if w not in common_words and len(w) > 2}

        search_keywords = extract_keywords(search_title_lower)
        latest_keywords = extract_keywords(latest_title_lower)

        # Check if there's overlap in keywords (e.g., "software" and "engineer")
        overlap = search_keywords.intersection(latest_keywords)

        # Accept if at least 50% of search keywords are in the actual title
        if len(search_keywords) == 0:
            return True

        overlap_ratio = len(overlap) / len(search_keywords)

        # Accept if 50%+ keywords match (e.g., searching "software engineer" matches "senior software engineer")
        return overlap_ratio >= 0.5

    def _infer_seniority(self, title: str) -> Optional[str]:
        """
        Infer seniority level from job title

        Args:
            title: Job title string

        Returns:
            Seniority level (intern, junior, senior, staff, principal, etc.)
        """
        if not title:
            return "junior"  # Default to junior if no title

        title_lower = title.lower()

        # Check for seniority keywords in order of specificity
        if "intern" in title_lower:
            return "intern"
        elif "junior" in title_lower or "jr" in title_lower or "associate" in title_lower:
            return "junior"
        elif "principal" in title_lower or "distinguished" in title_lower:
            return "principal"
        elif "staff" in title_lower:
            return "staff"
        elif "senior" in title_lower or "sr" in title_lower or "lead" in title_lower:
            return "senior"
        else:
            # Default to junior - experienced engineers usually specify their level
            return "junior"

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
