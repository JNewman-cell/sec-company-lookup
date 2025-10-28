"""
Database operations for secmap package.

This module handles all SQLite database operations including schema creation,
data loading, and complex search queries.
"""

import sqlite3
import time
import logging
from pathlib import Path
from typing import Dict, List, Any

from ..utils.utils import CACHE_DIR, normalize_cik

# Configure logging
logger = logging.getLogger(__name__)

# Database path
DB_PATH = CACHE_DIR / "secmap.db"


def init_database() -> None:
    """Initialize SQLite database optimized for search operations."""
    from ..utils.utils import ensure_cache_dir

    ensure_cache_dir()

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cik INTEGER,
            ticker TEXT,
            title TEXT,
            last_updated REAL,
            UNIQUE(cik, ticker)
        )
    """
    )

    # Create indexes optimized for search operations
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ticker ON companies(ticker)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_title ON companies(title)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cik ON companies(cik)")

    # Enable FTS (Full Text Search) for company names
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS companies_fts USING fts5(
            id, ticker, title, content='companies', content_rowid='id'
        )
    """
    )

    conn.commit()
    conn.close()


def load_data_to_db(data: Dict[str, Any]) -> None:
    """Load company data into SQLite database optimized for search operations."""
    init_database()

    conn = sqlite3.connect(DB_PATH)

    # Use transaction for better performance
    conn.execute("BEGIN TRANSACTION")

    try:
        # Clear existing data
        conn.execute("DELETE FROM companies")
        conn.execute("DELETE FROM companies_fts")

        # Insert new data in batches for better performance
        companies = []

        for key, company_info in data.items():
            if isinstance(company_info, dict):
                cik_raw = company_info.get("cik_str", "")
                ticker = company_info.get("ticker", "")
                title = company_info.get("title", "")

                cik_int = normalize_cik(cik_raw)

                if cik_int is not None and ticker and title:
                    companies.append((cik_int, ticker.upper(), title, time.time()))

        # Batch insert for better performance - let ID auto-increment
        conn.executemany(
            "INSERT INTO companies (cik, ticker, title, last_updated) VALUES (?, ?, ?, ?)",
            companies,
        )

        # Insert into FTS table - this will use the auto-generated IDs
        conn.execute(
            """
            INSERT INTO companies_fts (id, ticker, title)
            SELECT id, ticker, title FROM companies
        """
        )

        conn.execute("COMMIT")
        logger.info(f"Loaded {len(companies)} companies into database with FTS support")

    except Exception as e:
        conn.execute("ROLLBACK")
        logger.error(f"Failed to load data to database: {e}")
        raise
    finally:
        conn.close()


def search_companies_db(
    query: str, limit: int = 10, fuzzy: bool = True
) -> List[Dict[str, Any]]:
    """
    Search for companies in database using FTS and LIKE queries.

    Args:
        query: Search query string
        limit: Maximum number of results to return
        fuzzy: If True, perform fuzzy matching; if False, exact matching only

    Returns:
        List of matching company dictionaries
    """
    if not query or not query.strip():
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dict-like objects

    try:
        results = []

        if fuzzy:
            # Fuzzy search using FTS and LIKE queries
            # First try FTS for intelligent search
            cursor = conn.execute(
                """
                SELECT c.cik, c.ticker, c.title 
                FROM companies_fts fts
                JOIN companies c ON c.id = fts.id
                WHERE companies_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """,
                (query, limit),
            )

            for row in cursor:
                results.append(
                    {"cik": row["cik"], "ticker": row["ticker"], "title": row["title"]}
                )

            # If FTS didn't return enough results, fall back to LIKE search
            if len(results) < limit:
                remaining_limit = limit - len(results)
                seen_pairs = {(r["cik"], r["ticker"]) for r in results}

                # Search by ticker and name with LIKE, excluding already found results
                cursor = conn.execute(
                    """
                    SELECT cik, ticker, title
                    FROM companies 
                    WHERE (ticker LIKE ? OR title LIKE ?)
                    ORDER BY 
                        CASE 
                            WHEN ticker LIKE ? THEN 1 
                            WHEN title LIKE ? THEN 2 
                            ELSE 3 
                        END,
                        ticker
                    LIMIT ?
                """,
                    (
                        f"%{query}%",
                        f"%{query}%",
                        f"{query}%",
                        f"{query}%",
                        remaining_limit
                        * 2,  # Get more results to filter out duplicates
                    ),
                )

                added = 0
                for row in cursor:
                    if added >= remaining_limit:
                        break

                    # Skip if we already have this company from FTS results
                    if (row["cik"], row["ticker"]) not in seen_pairs:
                        results.append(
                            {
                                "cik": row["cik"],
                                "ticker": row["ticker"],
                                "title": row["title"],
                            }
                        )
                        seen_pairs.add((row["cik"], row["ticker"]))
                        added += 1
        else:
            # Exact matching only
            cursor = conn.execute(
                """
                SELECT cik, ticker, title
                FROM companies 
                WHERE LOWER(ticker) = LOWER(?) OR LOWER(title) = LOWER(?)
                ORDER BY ticker
                LIMIT ?
            """,
                (query, query, limit),
            )

            for row in cursor:
                results.append(
                    {"cik": row["cik"], "ticker": row["ticker"], "title": row["title"]}
                )

        return results

    except sqlite3.Error as e:
        logger.warning(f"Database search failed: {e}")
        raise
    finally:
        conn.close()


def get_companies_by_ciks_db(ciks: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    """
    Batch lookup companies by multiple CIK identifiers using database.

    Args:
        ciks: List of normalized CIK integers

    Returns:
        Dict mapping each CIK to list of matching companies
    """
    if not ciks:
        return {}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        # Batch query with IN clause
        placeholders = ",".join("?" * len(ciks))
        cursor = conn.execute(
            f"""
            SELECT cik, ticker, title
            FROM companies 
            WHERE cik IN ({placeholders})
            ORDER BY cik, ticker
        """,
            ciks,
        )

        results: Dict[int, List[Dict[str, Any]]] = {}
        for row in cursor:
            company = {
                "cik": row["cik"],
                "ticker": row["ticker"],
                "title": row["title"],
            }

            if row["cik"] not in results:
                results[row["cik"]] = []
            results[row["cik"]].append(company)

        # Ensure all requested CIKs are in the result (even if empty)
        for cik in ciks:
            if cik not in results:
                results[cik] = []

        return results

    except sqlite3.Error as e:
        logger.error(f"Database batch lookup failed: {e}")
        raise
    finally:
        conn.close()


def get_companies_by_company_names_db(
    company_names: List[str], fuzzy: bool = True
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Batch lookup companies by multiple company names using database.

    Args:
        company_names: List of company names
        fuzzy: If True, perform fuzzy matching; if False, exact matching only

    Returns:
        Dict mapping each company name to list of matching companies
    """
    if not company_names:
        return {}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        results: Dict[str, List[Dict[str, Any]]] = {}

        for company_name in company_names:
            if not company_name or not company_name.strip():
                results[company_name] = []
                continue

            if fuzzy:
                # Fuzzy matching with LIKE queries
                cursor = conn.execute(
                    """
                    SELECT cik, ticker, title
                    FROM companies 
                    WHERE LOWER(title) LIKE LOWER(?)
                    ORDER BY 
                        CASE 
                            WHEN LOWER(title) = LOWER(?) THEN 1
                            WHEN LOWER(title) LIKE LOWER(?) THEN 2
                            ELSE 3
                        END,
                        ticker
                """,
                    (
                        f"%{company_name.strip()}%",
                        company_name.strip(),
                        f"{company_name.strip()}%",
                    ),
                )
            else:
                # Exact matching only
                cursor = conn.execute(
                    """
                    SELECT cik, ticker, title
                    FROM companies 
                    WHERE LOWER(title) = LOWER(?)
                    ORDER BY ticker
                """,
                    (company_name.strip(),),
                )

            matches = []
            for row in cursor:
                matches.append(
                    {"cik": row["cik"], "ticker": row["ticker"], "title": row["title"]}
                )

            results[company_name] = matches

        return results

    except sqlite3.Error as e:
        logger.error(f"Database batch company name lookup failed: {e}")
        raise
    finally:
        conn.close()


def search_companies_by_company_name_db(
    company_name_query: str, limit: int = 10, fuzzy: bool = True
) -> List[Dict[str, Any]]:
    """
    Search for companies by company name using database with various matching options.

    Args:
        company_name_query: Company name search query
        limit: Maximum number of results
        fuzzy: If True, perform fuzzy matching; if False, exact matching only

    Returns:
        List of matching companies
    """
    if not company_name_query or not company_name_query.strip():
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        results = []

        if not fuzzy:
            # Exact match search
            cursor = conn.execute(
                """
                SELECT cik, ticker, title
                FROM companies 
                WHERE LOWER(title) = LOWER(?)
                ORDER BY ticker
                LIMIT ?
            """,
                (company_name_query.strip(), limit),
            )
        else:
            # Fuzzy search with ranking
            cursor = conn.execute(
                """
                SELECT cik, ticker, title,
                    CASE 
                        WHEN LOWER(title) = LOWER(?) THEN 1
                        WHEN LOWER(title) LIKE LOWER(?) THEN 2
                        WHEN LOWER(title) LIKE LOWER(?) THEN 3
                        ELSE 4
                    END as rank
                FROM companies 
                WHERE LOWER(title) LIKE LOWER(?)
                ORDER BY rank, ticker
                LIMIT ?
            """,
                (
                    company_name_query.strip(),
                    f"{company_name_query.strip()}%",
                    f"%{company_name_query.strip()}%",
                    f"%{company_name_query.strip()}%",
                    limit,
                ),
            )

        for row in cursor:
            results.append(
                {"cik": row["cik"], "ticker": row["ticker"], "title": row["title"]}
            )

        return results

    except sqlite3.Error as e:
        logger.error(f"Company name search failed: {e}")
        return []
    finally:
        conn.close()


def get_companies_by_sector_search_db(
    sector_keywords: List[str], limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search for companies by sector-related keywords in company names using database.

    Args:
        sector_keywords: List of keywords to search for
        limit: Maximum number of results

    Returns:
        List of matching companies
    """
    if not sector_keywords:
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        # Build search query for multiple keywords
        conditions = []
        params: List[Any] = []

        for keyword in sector_keywords:
            conditions.append("title LIKE ?")
            params.append(f"%{keyword}%")

        query = f"""
            SELECT cik, ticker, title
            FROM companies 
            WHERE {' OR '.join(conditions)}
            ORDER BY ticker
            LIMIT ?
        """
        params.append(limit)

        cursor = conn.execute(query, params)

        results = []
        for row in cursor:
            results.append(
                {"cik": row["cik"], "ticker": row["ticker"], "title": row["title"]}
            )

        return results

    except sqlite3.Error as e:
        logger.error(f"Sector search failed: {e}")
        return []
    finally:
        conn.close()


def get_db_stats() -> Dict[str, Any]:
    """Get database statistics."""
    from ..utils.utils import CACHE_DIR

    stats = {
        "db_exists": DB_PATH.exists(),
        "db_companies_count": 0,
        "db_fts_enabled": False,
        "cache_dir": str(CACHE_DIR),
    }

    if DB_PATH.exists():
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.execute("SELECT COUNT(*) FROM companies")
            stats["db_companies_count"] = cursor.fetchone()[0]

            # Check if FTS table exists and has data
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='table' AND name='companies_fts'
            """
            )
            if cursor.fetchone()[0] > 0:
                cursor = conn.execute("SELECT COUNT(*) FROM companies_fts")
                if cursor.fetchone()[0] > 0:
                    stats["db_fts_enabled"] = True

            conn.close()
        except sqlite3.Error as e:
            logger.warning(f"Failed to get database stats: {e}")

    return stats
