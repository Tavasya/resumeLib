"""
Search configuration for Google Custom Search API
Define job titles, companies, seniority levels, and exclusions
"""
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class SearchConfig:
    """Configuration for resume search queries"""

    # Job titles to search for
    job_titles: List[str] = field(default_factory=lambda: [
        "software engineer",
        "software developer",
        "data scientist",
        "machine learning engineer",
    ])

    # Seniority levels
    seniority_levels: List[str] = field(default_factory=lambda: [
        "intern",
        "junior",
        "senior",
        "staff",
        "principal",
    ])

    # Target companies (optional, empty = search all)
    companies: List[str] = field(default_factory=list)

    # File types to search
    file_types: List[str] = field(default_factory=lambda: ["pdf", "docx"])

    # Terms to exclude (templates, examples, etc.)
    # Keep this list SHORT - too many exclusions = 0 results
    exclude_terms: List[str] = field(default_factory=lambda: [
        "template",
        "example",
    ])

    # Number of results per search (max 10 per Google API)
    results_per_query: int = 10

    def build_search_queries(self) -> List[dict]:
        """
        Build search queries from configuration
        Prioritizes queries by seniority level (intern first, then junior, then senior)

        Returns:
            List of query configurations with metadata
        """
        queries = []

        # Build queries with seniority as outermost loop to prioritize intern queries
        for seniority in self.seniority_levels:
            for job_title in self.job_titles:
                for file_type in self.file_types:
                    query_parts = [
                        f'"{seniority} {job_title}"',
                        "resume OR CV",
                        f"filetype:{file_type}"
                    ]

                    # Add exclusions
                    for exclude in self.exclude_terms:
                        query_parts.append(f'-{exclude}')

                    # If companies are specified, create separate queries for each
                    if self.companies:
                        for company in self.companies:
                            company_query = query_parts.copy()
                            company_query.append(f'"{company}"')

                            queries.append({
                                "query": " ".join(company_query),
                                "job_title": job_title,
                                "seniority": seniority,
                                "company": company,
                                "file_type": file_type
                            })
                    else:
                        # No company filter
                        queries.append({
                            "query": " ".join(query_parts),
                            "job_title": job_title,
                            "seniority": seniority,
                            "company": None,
                            "file_type": file_type
                        })

        return queries
