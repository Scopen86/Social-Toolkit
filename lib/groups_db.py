"""Read Facebook group selections from the local groups SQLite database."""

from __future__ import annotations

import os
import sqlite3
from typing import Any

GROUP_COLUMNS = (
    "id, name, url, category, subcategory, is_managed, is_favorite, is_hidden"
)

CATEGORY_PREFS_SCHEMA = """
CREATE TABLE IF NOT EXISTS category_prefs (
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL DEFAULT '',
    is_favorite INTEGER NOT NULL DEFAULT 0,
    is_hidden INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (category, subcategory)
)
"""


def _connect(db_path: str) -> sqlite3.Connection:
    resolved = os.path.abspath(os.path.expanduser(db_path))
    if not os.path.isfile(resolved):
        raise FileNotFoundError(f"Groups database not found: {resolved}")
    connection = sqlite3.connect(resolved)
    connection.row_factory = sqlite3.Row
    _ensure_schema(connection)
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    """Add preference flags to older databases that predate them."""
    columns = {row[1] for row in connection.execute("PRAGMA table_info(groups)")}
    if "is_favorite" not in columns:
        connection.execute(
            "ALTER TABLE groups ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0"
        )
    if "is_hidden" not in columns:
        connection.execute(
            "ALTER TABLE groups ADD COLUMN is_hidden INTEGER NOT NULL DEFAULT 0"
        )
    connection.execute(CATEGORY_PREFS_SCHEMA)
    connection.commit()


def _where(category: str | None, subcategory: str | None, managed_only: bool):
    clauses: list[str] = []
    params: list[Any] = []
    if category:
        clauses.append("category = ?")
        params.append(category)
    if subcategory:
        clauses.append("subcategory = ?")
        params.append(subcategory)
    if managed_only:
        clauses.append("is_managed = 1")
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), params


def load_groups(
    db_path: str,
    category: str | None = None,
    subcategory: str | None = None,
    managed_only: bool = False,
) -> list[dict[str, Any]]:
    """Return matching group rows, favorites first, then ordered by name."""
    where, params = _where(category, subcategory, managed_only)
    sql = (
        f"SELECT {GROUP_COLUMNS} FROM groups{where} "
        "ORDER BY is_favorite DESC, is_hidden ASC, name COLLATE NOCASE"
    )
    with _connect(db_path) as connection:
        return [dict(row) for row in connection.execute(sql, params)]


def upsert_group(
    db_path: str,
    *,
    slug: str,
    name: str,
    url: str,
    category: str,
    subcategory: str = "",
) -> tuple[int, bool]:
    """Insert a group or refresh its name/URL/category.

    Returns ``(group_id, created)``.
    """
    slug = (slug or "").strip()
    if not slug:
        raise ValueError("A group slug is required.")
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT id FROM groups WHERE group_slug = ?", (slug,)
        ).fetchone()
        numeric = int(slug.isdigit())
        if row:
            connection.execute(
                "UPDATE groups SET name = ?, url = ?, is_numeric_id = ?, "
                "category = ?, subcategory = ? WHERE id = ?",
                (name, url, numeric, category, subcategory, row[0]),
            )
            return int(row[0]), False
        cursor = connection.execute(
            "INSERT INTO groups "
            "(group_slug, name, url, is_numeric_id, category, subcategory) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (slug, name, url, numeric, category, subcategory),
        )
        return int(cursor.lastrowid), True


def load_category_prefs(db_path: str) -> dict[tuple[str, str], dict[str, int]]:
    """Return category/subcategory favorite and hidden flags.

    Keys are ``(category, "")`` for categories and
    ``(category, subcategory)`` for subcategories.
    """
    with _connect(db_path) as connection:
        return {
            (row["category"], row["subcategory"]): {
                "is_favorite": row["is_favorite"],
                "is_hidden": row["is_hidden"],
            }
            for row in connection.execute(
                "SELECT category, subcategory, is_favorite, is_hidden "
                "FROM category_prefs"
            )
        }


def set_group_flags(
    db_path: str,
    group_id: int,
    favorite: bool | None = None,
    hidden: bool | None = None,
) -> None:
    """Update a group's favorite and/or hidden flag."""
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT is_favorite, is_hidden FROM groups WHERE id = ?", (group_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Group id not found: {group_id}")
        favorite_value = row[0] if favorite is None else int(bool(favorite))
        hidden_value = row[1] if hidden is None else int(bool(hidden))
        connection.execute(
            "UPDATE groups SET is_favorite = ?, is_hidden = ? WHERE id = ?",
            (favorite_value, hidden_value, group_id),
        )


def set_category_flags(
    db_path: str,
    category: str,
    subcategory: str = "",
    favorite: bool | None = None,
    hidden: bool | None = None,
) -> None:
    """Update a category or subcategory favorite/hidden flag."""
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT is_favorite, is_hidden FROM category_prefs "
            "WHERE category = ? AND subcategory = ?",
            (category, subcategory),
        ).fetchone()
        favorite_value = (row[0] if row else 0) if favorite is None else int(bool(favorite))
        hidden_value = (row[1] if row else 0) if hidden is None else int(bool(hidden))
        connection.execute(
            "INSERT OR REPLACE INTO category_prefs "
            "(category, subcategory, is_favorite, is_hidden) VALUES (?, ?, ?, ?)",
            (category, subcategory, favorite_value, hidden_value),
        )


def set_group_category(
    db_path: str,
    group_id: int,
    category: str,
    subcategory: str = "",
) -> None:
    """Update a group's category and/or subcategory."""
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT category, subcategory FROM groups WHERE id = ?", (group_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Group id not found: {group_id}")
        cat_value = category if category is not None else row[0]
        subcat_value = subcategory if subcategory is not None else row[1]
        connection.execute(
            "UPDATE groups SET category = ?, subcategory = ? WHERE id = ?",
            (cat_value, subcat_value, group_id),
        )


def set_favorite(db_path: str, group_id: int, favorite: bool) -> bool:
    """Mark a group as favorite (or not) and return the stored value."""
    set_group_flags(db_path, group_id, favorite=favorite)
    return bool(favorite)


def toggle_favorite(db_path: str, group_id: int) -> bool:
    """Flip a group's favorite flag and return the new value."""
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT is_favorite FROM groups WHERE id = ?", (group_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Group id not found: {group_id}")
        value = 0 if row[0] else 1
        connection.execute(
            "UPDATE groups SET is_favorite = ? WHERE id = ?", (value, group_id)
        )
    return bool(value)


def load_group_urls(
    db_path: str,
    category: str | None = None,
    subcategory: str | None = None,
    managed_only: bool = False,
    include_hidden: bool = False,
) -> list[str]:
    """Return unique, visible group URLs for the selected filters."""
    prefs = load_category_prefs(db_path)
    seen: set[str] = set()
    urls: list[str] = []
    for row in load_groups(db_path, category, subcategory, managed_only):
        row_category = (row.get("category") or "").strip()
        row_subcategory = (row.get("subcategory") or "").strip()
        if not include_hidden and (
            row.get("is_hidden")
            or prefs.get((row_category, ""), {}).get("is_hidden")
            or prefs.get((row_category, row_subcategory), {}).get("is_hidden")
        ):
            continue
        url = (row.get("url") or "").strip()
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def list_categories(db_path: str) -> list[str]:
    with _connect(db_path) as connection:
        rows = connection.execute(
            "SELECT DISTINCT category FROM groups "
            "WHERE category IS NOT NULL AND category != '' "
            "ORDER BY category COLLATE NOCASE"
        )
        return [row[0] for row in rows]


def list_subcategories(db_path: str, category: str | None = None) -> list[str]:
    with _connect(db_path) as connection:
        if category:
            rows = connection.execute(
                "SELECT DISTINCT subcategory FROM groups "
                "WHERE category = ? AND subcategory IS NOT NULL AND subcategory != '' "
                "ORDER BY subcategory COLLATE NOCASE",
                (category,),
            )
        else:
            rows = connection.execute(
                "SELECT DISTINCT subcategory FROM groups "
                "WHERE subcategory IS NOT NULL AND subcategory != '' "
                "ORDER BY subcategory COLLATE NOCASE"
            )
        return [row[0] for row in rows]
