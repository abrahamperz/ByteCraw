"""
ByteCraw — Universal scraping layer
===================================
A single API to scrape any site: static HTML, dynamic JS, hidden APIs,
session login, crawling at scale and Markdown conversion for LLMs.

Quickstart:

    from bytecraw import Scraper

    bot = Scraper()
    page = bot.fetch("https://books.toscrape.com")
    books = page.extract("article.product_pod", {
        "title": "h3 a::attr(title)",
        "price": "p.price_color::text",
    })

Explicit strategies:  bot.static(url) · bot.api(url) · bot.browser(url)
Crawling:             bot.crawl(url, item=..., fields=..., next=...)
LLM:                  page.markdown() · page.tokens()
"""

from .core import Scraper, Page, Session

__all__ = ["Scraper", "Page", "Session"]
__version__ = "0.1.0"
