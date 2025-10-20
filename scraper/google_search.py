"""
Google Custom Search API client for finding resumes
"""
from typing import List, Dict, Optional
import time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import settings


class GoogleSearchClient:
    """Client for Google Custom Search API"""

    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        self.cx = settings.GOOGLE_CX
        self.service = build("customsearch", "v1", developerKey=self.api_key)

    def search(
        self,
        query: str,
        num_results: int = 10,
        start_index: int = 1,
        date_restrict: str = "y5"
    ) -> List[Dict]:
        """
        Perform a search using Google Custom Search API

        Args:
            query: Search query string
            num_results: Number of results to return (1-10)
            start_index: Starting index for pagination (1-based)
            date_restrict: Filter by date (e.g., 'y5' = last 5 years, 'm6' = last 6 months)

        Returns:
            List of search result dictionaries containing title, link, snippet, etc.
        """
        try:
            # Execute the search with date filter
            result = (
                self.service.cse()
                .list(
                    q=query,
                    cx=self.cx,
                    num=num_results,
                    start=start_index,
                    dateRestrict=date_restrict
                )
                .execute()
            )

            # Extract items from response
            items = result.get("items", [])

            # Format results
            search_results = []
            for item in items:
                search_results.append({
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet"),
                    "file_format": item.get("fileFormat"),
                    "mime": item.get("mime"),
                })

            return search_results

        except HttpError as e:
            print(f"HTTP error during search: {e}")
            return []
        except Exception as e:
            print(f"Error during search: {e}")
            return []

    def search_with_pagination(
        self,
        query: str,
        max_results: int = 50,
        date_restrict: str = "y5"
    ) -> List[Dict]:
        """
        Perform a search with pagination to get more than 10 results

        Note: Google Custom Search API has a limit of 100 queries per day (free tier)
        and returns max 10 results per request.

        Args:
            query: Search query string
            max_results: Maximum number of results to retrieve (in multiples of 10)
            date_restrict: Filter by date (e.g., 'y5' = last 5 years)

        Returns:
            List of search result dictionaries
        """
        all_results = []
        start_index = 1
        num_per_request = 10

        while len(all_results) < max_results:
            results = self.search(
                query=query,
                num_results=num_per_request,
                start_index=start_index,
                date_restrict=date_restrict
            )

            if not results:
                # No more results
                break

            all_results.extend(results)
            start_index += num_per_request

            # Add a small delay to avoid rate limiting
            time.sleep(0.5)

        return all_results[:max_results]

    def search_multiple_queries(
        self,
        queries: List[Dict],
        results_per_query: int = 10,
        delay_between_queries: float = 1.0
    ) -> Dict[str, List[Dict]]:
        """
        Search multiple queries with delay between requests

        Args:
            queries: List of query dictionaries from SearchConfig.build_search_queries()
            results_per_query: Number of results per query
            delay_between_queries: Seconds to wait between queries (avoid rate limiting)

        Returns:
            Dictionary mapping query strings to their results
        """
        results = {}

        for i, query_config in enumerate(queries):
            query = query_config["query"]
            print(f"Searching ({i+1}/{len(queries)}): {query}")

            search_results = self.search(query, num_results=results_per_query)

            # Store results with metadata
            results[query] = {
                "results": search_results,
                "metadata": query_config
            }

            print(f"  Found {len(search_results)} results")

            # Delay between requests (except for the last one)
            if i < len(queries) - 1:
                time.sleep(delay_between_queries)

        return results


# Global client instance
google_search_client = GoogleSearchClient()
