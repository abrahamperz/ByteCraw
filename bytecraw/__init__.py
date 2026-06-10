"""
ByteCraw — Universal scraping layer
===================================
Una sola API para scrapear cualquier sitio: HTML estático, JS dinámico,
APIs, login con sesión, crawling a escala y conversión a Markdown para LLMs.

Uso rápido:

    from bytecraw import Scraper

    bot = Scraper()
    page = bot.fetch("https://books.toscrape.com")
    libros = page.extract("article.product_pod", {
        "titulo": "h3 a::attr(title)",
        "precio": "p.price_color::text",
    })

Estrategias explícitas:  bot.static(url) · bot.api(url) · bot.browser(url)
Crawling:                bot.crawl(url, item=..., fields=..., next=...)
LLM:                     page.markdown() · page.tokens()
"""

from .core import Scraper, Page, Session

__all__ = ["Scraper", "Page", "Session"]
__version__ = "0.1.0"
