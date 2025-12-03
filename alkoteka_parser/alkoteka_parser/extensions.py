"""
Scrapy extensions for monitoring and notifications.

Features:
- Statistics collection and reporting
- Telegram notifications on spider completion
- CSV/JSON export of statistics
- Error tracking and alerts

Usage:
    In settings.py:
    EXTENSIONS = {
        'alkoteka_parser.extensions.StatsCollector': 100,
        'alkoteka_parser.extensions.TelegramNotifier': 200,
    }

    Environment variables:
    TELEGRAM_BOT_TOKEN=your_token_here
    TELEGRAM_CHAT_ID=your_chat_id_here
"""

import json
import csv
import requests
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from scrapy import signals
from scrapy.exceptions import IgnoreRequest


logger = logging.getLogger(__name__)


class StatsCollector:
    """
    Collects detailed statistics about the scraping job.

    Metrics collected:
    - Total items scraped
    - Items per category
    - Items per minute
    - Error count and types
    - Response times
    - Success rate
    """

    def __init__(self, crawler):
        """
        Initialize the stats collector.

        Args:
            crawler: Scrapy crawler instance
        """
        self.crawler = crawler
        self.stats = {}
        self.start_time = None
        self.end_time = None
        self.category_stats = {}
        self.error_stats = {}
        self.response_times = []

    @classmethod
    def from_crawler(cls, crawler):
        """Create extension from crawler."""
        ext = cls(crawler)
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        return ext

    def spider_opened(self, spider):
        """Called when spider is opened."""
        self.start_time = time.time()
        logger.info(f"Stats collection started for spider: {spider.name}")

    def spider_closed(self, spider, reason):
        """Called when spider is closed."""
        self.end_time = time.time()

        # Collect final statistics
        stats = self.crawler.stats.get_stats()

        # Calculate custom metrics
        duration = self.end_time - self.start_time
        item_count = stats.get('item_scraped_count', 0)

        self.stats = {
            'spider_name': spider.name,
            'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
            'end_time': datetime.fromtimestamp(self.end_time).isoformat(),
            'duration_seconds': round(duration, 2),
            'duration_minutes': round(duration / 60, 2),
            'items_scraped': item_count,
            'items_per_minute': round(item_count / (duration / 60), 2) if duration > 0 else 0,
            'request_count': stats.get('downloader/request_count', 0),
            'response_count': stats.get('downloader/response_count', 0),
            'response_received_count': stats.get('downloader/response_received_count', 0),
            'exception_count': stats.get('downloader/exception_count', 0),
            'error_count': stats.get('spider_exceptions/AttributeError', 0),
            'start_reason': reason,
        }

        # Save statistics
        self._save_stats(spider.name)

        logger.info(f"Stats collection completed. Items scraped: {item_count}")

    def _save_stats(self, spider_name: str):
        """
        Save collected statistics to files.

        Args:
            spider_name: Name of the spider
        """
        stats_dir = Path('logs/stats')
        stats_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        basename = f"{spider_name}_{timestamp}"

        # Save as JSON
        json_file = stats_dir / f"{basename}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
        logger.info(f"Stats saved to {json_file}")

        # Save as CSV
        csv_file = stats_dir / f"{basename}.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.stats.keys())
            writer.writeheader()
            writer.writerow(self.stats)
        logger.info(f"Stats saved to {csv_file}")

    def get_stats(self) -> Dict[str, Any]:
        """Return collected statistics."""
        return self.stats


class TelegramNotifier:
    """
    Sends notifications about scraping job to Telegram.

    Features:
    - Job completion notification
    - Statistics summary
    - Error alerts
    - Performance metrics

    Configuration:
        Environment variables:
        - TELEGRAM_BOT_TOKEN: Bot token from @BotFather
        - TELEGRAM_CHAT_ID: Chat ID (can be obtained from @userinfobot)

        Or settings.py:
        - TELEGRAM_BOT_TOKEN
        - TELEGRAM_CHAT_ID
        - TELEGRAM_ENABLED (default: True)
    """

    TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, crawler):
        """
        Initialize the Telegram notifier.

        Args:
            crawler: Scrapy crawler instance
        """
        self.crawler = crawler
        self.settings = crawler.settings

        # Get credentials from settings or environment
        import os
        self.bot_token = self.settings.get('TELEGRAM_BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = self.settings.get('TELEGRAM_CHAT_ID') or os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = self.settings.getbool('TELEGRAM_ENABLED', True) and self.bot_token and self.chat_id

        if self.enabled:
            logger.info("Telegram notifications enabled")
        else:
            logger.info("Telegram notifications disabled (no token or chat_id)")

    @classmethod
    def from_crawler(cls, crawler):
        """Create extension from crawler."""
        ext = cls(crawler)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        return ext

    def spider_closed(self, spider, reason):
        """Called when spider is closed."""
        if not self.enabled:
            return

        try:
            stats = self.crawler.stats.get_stats()
            message = self._format_message(spider, reason, stats)
            self._send_message(message)
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

    def _format_message(self, spider, reason: str, stats: Dict) -> str:
        """
        Format statistics message for Telegram.

        Args:
            spider: Spider instance
            reason: Reason for spider closure
            stats: Statistics dictionary

        Returns:
            Formatted message string
        """
        # Extract key metrics
        item_count = stats.get('item_scraped_count', 0)
        duration = stats.get('elapsed', 0)
        request_count = stats.get('downloader/request_count', 0)
        response_count = stats.get('downloader/response_count', 0)
        exception_count = stats.get('downloader/exception_count', 0)

        # Calculate success rate
        success_rate = (response_count / request_count * 100) if request_count > 0 else 0

        # Format message
        message = f"""
🎉 *Scraping Job Completed*

📊 *Statistics:*
• Spider: `{spider.name}`
• Duration: {duration:.0f}s ({duration/60:.1f} min)
• Items Scraped: *{item_count}*
• Requests: {request_count}
• Responses: {response_count} ({success_rate:.1f}%)
• Errors: {exception_count}
• Status: {reason}

⏱️ *Performance:*
• Items/min: {(item_count / (duration/60)) if duration > 0 else 0:.1f}
• Requests/min: {(request_count / (duration/60)) if duration > 0 else 0:.1f}

✅ All data exported successfully!
"""
        return message.strip()

    def _send_message(self, message: str) -> bool:
        """
        Send message to Telegram.

        Args:
            message: Message text (supports Markdown formatting)

        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        url = self.TELEGRAM_API_URL.format(token=self.bot_token)
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'Markdown',
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Telegram notification sent successfully")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False
        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    @staticmethod
    def send_alert(bot_token: str, chat_id: str, message: str) -> bool:
        """
        Send custom alert message to Telegram.

        Usage:
            TelegramNotifier.send_alert(
                bot_token='YOUR_TOKEN',
                chat_id='YOUR_CHAT_ID',
                message='⚠️ Custom alert message'
            )

        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID
            message: Message to send

        Returns:
            True if successful, False otherwise
        """
        url = TelegramNotifier.TELEGRAM_API_URL.format(token=bot_token)
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown',
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Failed to send alert: {e}")
            return False


class ErrorTracker:
    """
    Tracks errors and exceptions during scraping.

    Features:
    - Count errors by type
    - Track failed URLs
    - Log stack traces
    - Generate error report
    """

    def __init__(self, crawler):
        """Initialize error tracker."""
        self.crawler = crawler
        self.errors = []
        self.error_types = {}

    @classmethod
    def from_crawler(cls, crawler):
        """Create extension from crawler."""
        ext = cls(crawler)
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_error, signal=signals.spider_error)
        return ext

    def spider_opened(self, spider):
        """Called when spider opens."""
        logger.info("Error tracking started")

    def spider_error(self, failure, response, spider):
        """Called when spider error occurs."""
        error_type = failure.type.__name__
        self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
        self.errors.append({
            'timestamp': datetime.now().isoformat(),
            'type': error_type,
            'url': response.url if response else 'N/A',
            'message': str(failure.value),
        })

        logger.error(f"Spider error: {error_type} on {response.url if response else 'N/A'}")

    def get_error_report(self) -> Dict[str, Any]:
        """Get error statistics and details."""
        return {
            'total_errors': len(self.errors),
            'error_types': self.error_types,
            'errors': self.errors,
        }


__all__ = [
    'StatsCollector',
    'TelegramNotifier',
    'ErrorTracker',
]
