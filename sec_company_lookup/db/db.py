"""
Database operations for sec-company-lookup package.

This module handles all SQLite database operations including schema creation,
data loading, and complex search queries.
"""

import sqlite3
import time
import logging
from typing import Dict, List, Any, cast, Tuple
from contextlib import contextmanager

from ..types import SECCompanyInfo, CompanyData
from ..utils.utils import CACHE_DIR, normalize_cik

# Configure logging
logger = logging.getLogger(__name__)

# Database path
DB_PATH = CACHE_DIR / "sec_company_lookup.db"


@contextmanager
def get_db_connection(row_factory: bool = True):
    """
    Context manager for database connections.
    
    Args:
        row_factory: If True, set row_factory to sqlite3.Row for dict-like access
        
    Yields:
        sqlite3.Connection: Database connection
        
    Example:
        >>> with get_db_connection() as conn:
        >>>     cursor = conn.execute("SELECT * FROM companies")
        >>>     results = cursor.fetchall()
    """
    conn = sqlite3.connect(DB_PATH)
    if row_factory:
        conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database() -> None:
    """Initialize SQLite database optimized for search operations."""
    from ..utils.utils import ensure_cache_dir

    ensure_cache_dir()

    with get_db_connection(row_factory=False) as conn:
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


def load_data_to_db(data: Dict[str, Any]) -> None:
    """Load company data into SQLite database optimized for search operations."""
    init_database()

    with get_db_connection(row_factory=False) as conn:
        # Use transaction for better performance
        conn.execute("BEGIN TRANSACTION")

        try:
            # Clear existing data
            conn.execute("DELETE FROM companies")
            conn.execute("DELETE FROM companies_fts")

            # Insert new data in batches for better performance
            companies: List[Tuple[int, str, str, float]] = []

            for _, company_info in data.items():
                if isinstance(company_info, dict):
                    # Type cast to get proper typing support
                    sec_info = cast(SECCompanyInfo, company_info)
                    cik_raw: str = sec_info.get("cik_str", "") or ""
                    ticker: str = sec_info.get("ticker", "") or ""
                    title: str = sec_info.get("title", "") or ""

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


def search_companies_db(
    query: str, limit: int = 10, fuzzy: bool = True
) -> List[CompanyData]:
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

    with get_db_connection() as conn:
        try:
            results: List[CompanyData] = []

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
                        {"cik": row["cik"], "ticker": row["ticker"], "name": row["title"]}
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
                                    "name": row["title"],
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
                        {"cik": row["cik"], "ticker": row["ticker"], "name": row["title"]}
                    )

            return results

        except sqlite3.Error as e:
            logger.warning(f"Database search failed: {e}")
            raise


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

    with get_db_connection() as conn:
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
                    "name": row["title"],
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

    with get_db_connection() as conn:
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

                matches: List[Dict[str, Any]] = []
                for row in cursor:
                    matches.append(
                        {"cik": row["cik"], "ticker": row["ticker"], "name": row["title"]}
                    )

                results[company_name] = matches

            return results

        except sqlite3.Error as e:
            logger.error(f"Database batch company name lookup failed: {e}")
            raise
        
def get_companies_by_tickers_db(
    tickers: List[str]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Batch lookup companies by multiple tickers using database.

    Args:
        tickers: List of ticker strings

    Returns:
        Dict mapping each ticker to list of matching companies
    """
    if not tickers:
        return {}

    with get_db_connection() as conn:
        try:
            # Batch query with IN clause
            placeholders = ",".join("?" * len(tickers))
            cursor = conn.execute(
                f"""
                SELECT cik, ticker, title
                FROM companies
                WHERE ticker IN ({placeholders})
                ORDER BY ticker
            """,
                tickers,
            )

            results: Dict[str, List[Dict[str, Any]]] = {}
            for row in cursor:
                company = {
                    "cik": row["cik"],
                    "ticker": row["ticker"],
                    "name": row["title"],
                }

                if row["ticker"] not in results:
                    results[row["ticker"]] = []
                results[row["ticker"]].append(company)

            # Ensure all requested tickers are in the result (even if empty)
            for ticker in tickers:
                if ticker not in results:
                    results[ticker] = []

            return results

        except sqlite3.Error as e:
            logger.error(f"Database batch ticker lookup failed: {e}")
            raise


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

    with get_db_connection() as conn:
        try:
            results: List[Dict[str, Any]] = []

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
                    {"cik": row["cik"], "ticker": row["ticker"], "name": row["title"]}
                )

            return results

        except sqlite3.Error as e:
            logger.error(f"Company name search failed: {e}")
            return []


def get_db_stats() -> Dict[str, Any]:
    """Get database statistics."""
    from ..utils.utils import CACHE_DIR

    stats: Dict[str, Any] = {
        "db_exists": DB_PATH.exists(),
        "db_companies_count": 0,
        "db_fts_enabled": False,
        "cache_dir": str(CACHE_DIR),
    }

    if DB_PATH.exists():
        try:
            with get_db_connection(row_factory=False) as conn:
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

        except sqlite3.Error as e:
            logger.warning(f"Failed to get database stats: {e}")

    return stats
