"""
Técnica 4 — Scrapy: scraping a escala
======================================
Cuando ya no es una página sino miles. Scrapy maneja por ti la cola de URLs,
la concurrencia (varias peticiones en paralelo), reintentos, rate limiting y
la exportación de datos. Es la diferencia entre un script y un crawler industrial.

Normalmente Scrapy se usa con un proyecto completo (scrapy startproject ...),
pero aquí lo dejamos en un solo archivo ejecutable para practicar.

Sitio de práctica: https://quotes.toscrape.com (con paginación)

Antes de correr:  pip install scrapy
Correr:           python 04_scrapy_spider.py
Genera:           frases_scrapy.json
"""

import scrapy
from scrapy.crawler import CrawlerProcess


class FrasesSpider(scrapy.Spider):
    name = "frases"
    start_urls = ["https://quotes.toscrape.com/"]

    # Buenas prácticas integradas en Scrapy: identifícate y no martilles el server
    custom_settings = {
        "USER_AGENT": "practica-scraping (+https://ejemplo.com)",
        "DOWNLOAD_DELAY": 0.5,        # espera entre peticiones
        "CONCURRENT_REQUESTS": 4,      # peticiones en paralelo
        "AUTOTHROTTLE_ENABLED": True,  # ajusta la velocidad solo
        "FEEDS": {"frases_scrapy.json": {"format": "json", "overwrite": True}},
    }

    def parse(self, response):
        # yield de cada item -> Scrapy los junta y exporta solo
        for q in response.css("div.quote"):
            yield {
                "frase": q.css("span.text::text").get(),
                "autor": q.css("small.author::text").get(),
                "tags": q.css("a.tag::text").getall(),
            }

        # Seguir a la siguiente página: Scrapy encola la URL automáticamente
        siguiente = response.css("li.next a::attr(href)").get()
        if siguiente:
            yield response.follow(siguiente, callback=self.parse)


if __name__ == "__main__":
    proceso = CrawlerProcess()
    proceso.crawl(FrasesSpider)
    proceso.start()
    print("\nGuardado en frases_scrapy.json")
