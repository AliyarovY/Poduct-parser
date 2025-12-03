"""
Database pipelines and utilities for storing scraped data.

Supports:
- SQLite database storage
- Automatic table creation
- Data type inference
- Transaction batching

Usage:
    In settings.py:
    ITEM_PIPELINES = {
        'alkoteka_parser.database.SqlitePipeline': 600,
    }

    Database settings:
    DATABASE_NAME = 'products.db'
    DATABASE_BATCH_SIZE = 100
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from scrapy.exceptions import DropItem


logger = logging.getLogger(__name__)


class SqlitePipeline:
    """
    Pipeline to store items in SQLite database.

    Features:
    - Automatic table creation
    - Type inference from data
    - Batch inserts for performance
    - JSON serialization for complex fields
    """

    def __init__(self, database_name: str, batch_size: int = 100):
        """
        Initialize SQLite pipeline.

        Args:
            database_name: Path to SQLite database file
            batch_size: Number of items to batch before committing
        """
        self.database_name = database_name
        self.batch_size = batch_size
        self.connection = None
        self.cursor = None
        self.batch = []
        self.table_created = False

    @classmethod
    def from_crawler(cls, crawler):
        """Create pipeline from crawler."""
        database_name = crawler.settings.get('DATABASE_NAME', 'products.db')
        batch_size = crawler.settings.getint('DATABASE_BATCH_SIZE', 100)
        return cls(database_name, batch_size)

    def open_spider(self, spider):
        """Called when spider is opened."""
        self.connection = sqlite3.connect(self.database_name)
        self.cursor = self.connection.cursor()
        logger.info(f"SQLite database opened: {self.database_name}")

    def close_spider(self, spider):
        """Called when spider is closed."""
        if self.batch:
            self._flush_batch()

        if self.connection:
            self.connection.close()
        logger.info(f"SQLite database closed. Items stored in {self.database_name}")

    def process_item(self, item, spider):
        """
        Process item and store in database.

        Args:
            item: Scrapy item
            spider: Spider instance

        Returns:
            Processed item
        """
        # Convert item to dict
        item_dict = dict(item)

        # Create table if needed
        if not self.table_created:
            self._create_table(item_dict)
            self.table_created = True

        # Add to batch
        self.batch.append(item_dict)

        # Flush batch if full
        if len(self.batch) >= self.batch_size:
            self._flush_batch()

        return item

    def _create_table(self, item: Dict[str, Any]):
        """
        Create database table based on item structure.

        Args:
            item: Sample item to infer schema from
        """
        # Infer column types
        columns = []
        for key, value in item.items():
            col_type = self._infer_type(value)
            columns.append(f'"{key}" {col_type}')

        columns_sql = ', '.join(columns)
        table_sql = f'''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {columns_sql},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''

        try:
            self.cursor.execute(table_sql)
            self.connection.commit()
            logger.info("Database table created successfully")
        except sqlite3.Error as e:
            logger.error(f"Failed to create table: {e}")
            raise

    def _infer_type(self, value: Any) -> str:
        """
        Infer SQLite type from Python value.

        Args:
            value: Value to infer type from

        Returns:
            SQLite type string
        """
        if value is None:
            return 'TEXT'
        elif isinstance(value, bool):
            return 'BOOLEAN'
        elif isinstance(value, int):
            return 'INTEGER'
        elif isinstance(value, float):
            return 'REAL'
        elif isinstance(value, (dict, list)):
            return 'TEXT'  # Store as JSON string
        else:
            return 'TEXT'

    def _flush_batch(self):
        """Insert batched items into database."""
        if not self.batch:
            return

        try:
            # Prepare insert statement
            first_item = self.batch[0]
            columns = list(first_item.keys())
            placeholders = ', '.join(['?' for _ in columns])
            columns_sql = ', '.join([f'"{col}"' for col in columns])

            insert_sql = f'INSERT INTO products ({columns_sql}) VALUES ({placeholders})'

            # Prepare values
            values = []
            for item in self.batch:
                row_values = []
                for col in columns:
                    value = item.get(col)
                    # Serialize complex types as JSON
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, ensure_ascii=False, default=str)
                    row_values.append(value)
                values.append(tuple(row_values))

            # Execute batch insert
            self.cursor.executemany(insert_sql, values)
            self.connection.commit()

            logger.info(f"Inserted {len(self.batch)} items into database")
            self.batch = []

        except sqlite3.Error as e:
            logger.error(f"Failed to insert items: {e}")
            self.batch = []
            raise

    def export_to_json(self, output_file: str) -> int:
        """
        Export all items from database to JSON.

        Args:
            output_file: Path to output JSON file

        Returns:
            Number of items exported
        """
        try:
            self.cursor.execute('SELECT * FROM products ORDER BY id DESC')
            rows = self.cursor.fetchall()

            if not rows:
                logger.warning("No items found in database")
                return 0

            # Get column names
            column_names = [description[0] for description in self.cursor.description]

            # Convert rows to dicts
            items = []
            for row in rows:
                item = dict(zip(column_names, row))
                items.append(item)

            # Write to JSON
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(items, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"Exported {len(items)} items to {output_file}")
            return len(items)

        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with statistics
        """
        try:
            # Get total items
            self.cursor.execute('SELECT COUNT(*) FROM products')
            total_items = self.cursor.fetchone()[0]

            # Get latest item
            self.cursor.execute('SELECT created_at FROM products ORDER BY id DESC LIMIT 1')
            result = self.cursor.fetchone()
            latest_item = result[0] if result else None

            return {
                'total_items': total_items,
                'latest_item': latest_item,
                'database_file': self.database_name,
            }

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}


class DatabaseManager:
    """
    Utility class for database operations.

    Usage:
        manager = DatabaseManager('products.db')
        stats = manager.get_statistics()
        items = manager.query('SELECT * FROM products LIMIT 10')
    """

    def __init__(self, database_name: str):
        """Initialize database manager."""
        self.database_name = database_name
        self.connection = None

    def connect(self):
        """Connect to database."""
        try:
            self.connection = sqlite3.connect(self.database_name)
            self.connection.row_factory = sqlite3.Row
            logger.info(f"Connected to database: {self.database_name}")
        except sqlite3.Error as e:
            logger.error(f"Failed to connect: {e}")
            raise

    def disconnect(self):
        """Disconnect from database."""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from database")

    def query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """
        Execute query and return results.

        Args:
            sql: SQL query
            params: Query parameters

        Returns:
            List of result dictionaries
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Query failed: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            cursor = self.connection.cursor()

            # Get table info
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            stats = {
                'database': self.database_name,
                'tables': tables,
                'items_count': 0,
            }

            if 'products' in tables:
                cursor.execute('SELECT COUNT(*) FROM products')
                stats['items_count'] = cursor.fetchone()[0]

            return stats

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}

    def export_to_csv(self, output_file: str, table: str = 'products') -> int:
        """
        Export table to CSV.

        Args:
            output_file: Path to output CSV file
            table: Table name

        Returns:
            Number of rows exported
        """
        import csv

        try:
            cursor = self.connection.cursor()
            cursor.execute(f'SELECT * FROM {table}')

            rows = cursor.fetchall()
            if not rows:
                logger.warning(f"No data in table {table}")
                return 0

            column_names = [description[0] for description in cursor.description]

            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=column_names)
                writer.writeheader()

                for row in rows:
                    row_dict = dict(zip(column_names, row))
                    writer.writerow(row_dict)

            logger.info(f"Exported {len(rows)} rows to {output_file}")
            return len(rows)

        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            return 0


__all__ = [
    'SqlitePipeline',
    'DatabaseManager',
]
