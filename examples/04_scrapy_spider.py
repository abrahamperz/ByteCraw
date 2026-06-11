"""
Technique 4 — Scrapy: scraping at scale
=======================================
When it's no longer one page but thousands. Scrapy handles the URL queue,
concurrency (parallel requests), retries, rate limiting and data export for
you. It's the difference between a script and an industrial crawler.

Scrapy is normally used as a full project (scrapy startproject ...), but
here we keep it in a single runnable file for practice.

Practice site: https://quotes.toscrape.com (with pagination)

Before running:  pip install scrapy
Run:             python 04_scrapy_spider.py
Generates:       frases_scrapy.json
"""

import scrapy
from scrapy.crawler import CrawlerProcess


class QuotesSpider(scrapy.Spider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com/"]

    # Good practices built into Scrapy: identify yourself and don't hammer the server
    custom_settings = {
        "USER_AGENT": "scraping-practice (+https://example.com)",
        "DOWNLOAD_DELAY": 0.5,        # wait between requests
        "CONCURRENT_REQUESTS": 4,      # parallel requests
        "AUTOTHROTTLE_ENABLED": True,  # auto-adjusts the speed
        "FEEDS": {"frases_scrapy.json": {"format": "json", "overwrite": True}},
    }

    def parse(self, response):
        # yield each item -> Scrapy collects and exports them on its own
        for q in response.css("div.quote"):
            yield {
                "quote": q.css("span.text::text").get(),
                "author": q.css("small.author::text").get(),
                "tags": q.css("a.tag::text").getall(),
            }

        # Follow the next page: Scrapy queues the URL automatically
        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)


if __name__ == "__main__":
    process = CrawlerProcess()
    process.crawl(QuotesSpider)
    process.start()
    print("\nSaved to frases_scrapy.json")
