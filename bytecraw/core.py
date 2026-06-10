"""
Núcleo de la librería ByteCraw.

Diseño: un objeto Scraper que sabe obtener una página con la estrategia que
quieras (o la mejor automáticamente) y te devuelve un objeto Page sobre el que
extraes datos con selectores CSS sencillos.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

import requests
from bs4 import BeautifulSoup

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

def _decoded_html(r: requests.Response) -> str:
    """Texto de la respuesta con la codificación correcta.

    requests cae a ISO-8859-1 cuando el header no trae charset (RFC 2616), lo
    que rompe UTF-8 (£ -> Â£). Si pasa eso, usamos la detección por contenido.
    """
    if r.encoding is None or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding
    return r.text


# Parsea selectores tipo "p.price::text" o "h3 a::attr(title)"
_PSEUDO = re.compile(r"^(?P<sel>.*?)(?:::(?P<op>text|attr)\((?P<arg>[^)]*)\)|::(?P<op2>text))?$")


def _split_selector(spec: str) -> tuple[str, str, str | None]:
    """Devuelve (selector_css, operacion, argumento).

    operacion: "text" (por defecto) o "attr". argumento: nombre del atributo.
    Ejemplos:
      "p.price_color::text"   -> ("p.price_color", "text", None)
      "h3 a::attr(title)"     -> ("h3 a", "attr", "title")
      "div.quote"             -> ("div.quote", "text", None)
    """
    spec = spec.strip()
    if "::attr(" in spec:
        sel, rest = spec.split("::attr(", 1)
        return sel.strip(), "attr", rest.rstrip(")").strip()
    if spec.endswith("::text"):
        return spec[: -len("::text")].strip(), "text", None
    return spec, "text", None


def _value_from(node, op: str, arg: str | None) -> str | None:
    if node is None:
        return None
    if op == "attr":
        return node.get(arg)
    return node.get_text(strip=True)


@dataclass
class Page:
    """Una página ya descargada. Sobre ella extraes datos."""

    url: str
    html: str = ""
    data: Any = None          # JSON si vino de una API
    method: str = "static"    # static | api | browser
    elapsed: float = 0.0
    status: int = 200
    _soup: BeautifulSoup | None = field(default=None, repr=False)

    @property
    def soup(self) -> BeautifulSoup:
        if self._soup is None:
            self._soup = BeautifulSoup(self.html or "", "lxml")
        return self._soup

    # --- extracción ---------------------------------------------------------
    def css(self, spec: str) -> str | None:
        """Primer match de un selector. Soporta ::text y ::attr(nombre)."""
        sel, op, arg = _split_selector(spec)
        return _value_from(self.soup.select_one(sel), op, arg)

    def css_all(self, spec: str) -> list[str]:
        """Todos los matches de un selector."""
        sel, op, arg = _split_selector(spec)
        return [v for n in self.soup.select(sel) if (v := _value_from(n, op, arg)) is not None]

    def extract(self, item: str, fields: dict[str, str]) -> list[dict]:
        """Extrae una lista de registros.

        item:   selector CSS que delimita cada registro (ej. "article.product_pod").
        fields: dict {nombre: selector_relativo}. El selector se aplica DENTRO de
                cada item. Si un campo termina en "[]" devuelve lista de valores.

        Ejemplo:
            page.extract("div.quote", {
                "frase": "span.text::text",
                "autor": "small.author::text",
                "tags[]": "a.tag::text",
            })
        """
        registros = []
        for nodo in self.soup.select(item):
            fila = {}
            for nombre, spec in fields.items():
                sel, op, arg = _split_selector(spec)
                if nombre.endswith("[]"):
                    fila[nombre[:-2]] = [
                        v for n in nodo.select(sel) if (v := _value_from(n, op, arg)) is not None
                    ]
                else:
                    fila[nombre] = _value_from(nodo.select_one(sel), op, arg)
            registros.append(fila)
        return registros

    def links(self) -> list[str]:
        return [a["href"] for a in self.soup.select("a[href]")]

    def json(self) -> Any:
        return self.data

    # --- LLM ----------------------------------------------------------------
    def markdown(self, main_only: bool = True) -> str:
        """Convierte la página a Markdown limpio (ahorra tokens para LLMs)."""
        if main_only:
            try:
                import trafilatura

                md = trafilatura.extract(self.html, output_format="markdown")
                if md:
                    return md
            except ImportError:
                pass
        from markdownify import markdownify

        return markdownify(self.html, strip=["script", "style"])

    def tokens(self, of: str | None = None) -> int:
        """Estimación rápida de tokens (~4 chars/token)."""
        texto = of if of is not None else (self.html or "")
        return len(texto) // 4


class Session:
    """Sesión autenticada reutilizable (cookies + headers persisten)."""

    def __init__(self, scraper: "Scraper"):
        self._s = requests.Session()
        self._s.headers.update({"User-Agent": scraper.user_agent})
        self._scraper = scraper

    def login(self, url: str, data: dict, csrf_field: str | None = None) -> "Session":
        """Hace login. Si csrf_field se indica, lo lee del formulario primero."""
        if csrf_field:
            r = self._s.get(url, timeout=self._scraper.timeout)
            token = BeautifulSoup(_decoded_html(r), "lxml").select_one(f'input[name="{csrf_field}"]')
            if token:
                data = {**data, csrf_field: token["value"]}
        self._s.post(url, data=data, timeout=self._scraper.timeout)
        return self

    def bearer(self, token: str) -> "Session":
        self._s.headers["Authorization"] = f"Bearer {token}"
        return self

    def fetch(self, url: str) -> Page:
        t0 = time.perf_counter()
        r = self._s.get(url, timeout=self._scraper.timeout)
        r.raise_for_status()
        return Page(url=url, html=_decoded_html(r), method="static",
                    elapsed=round(time.perf_counter() - t0, 3), status=r.status_code)


class Scraper:
    """Punto de entrada. Elige la estrategia o deja que decida sola."""

    def __init__(self, user_agent: str = DEFAULT_UA, delay: float = 0.0, timeout: int = 15):
        self.user_agent = user_agent
        self.delay = delay
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": user_agent})

    # --- estrategias --------------------------------------------------------
    def static(self, url: str) -> Page:
        """Técnica 1: HTML estático con requests."""
        t0 = time.perf_counter()
        r = self._session.get(url, timeout=self.timeout)
        r.raise_for_status()
        self._wait()
        return Page(url=url, html=_decoded_html(r), method="static",
                    elapsed=round(time.perf_counter() - t0, 3), status=r.status_code)

    def api(self, url: str, params: dict | None = None) -> Page:
        """Técnica 3: pide una API y guarda el JSON."""
        t0 = time.perf_counter()
        r = self._session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        self._wait()
        return Page(url=url, data=r.json(), method="api",
                    elapsed=round(time.perf_counter() - t0, 3), status=r.status_code)

    def browser(self, url: str, wait: str | None = None, scroll: bool = False) -> Page:
        """Técnica 2: navegador real (Playwright) para sitios con JS."""
        from playwright.sync_api import sync_playwright

        t0 = time.perf_counter()
        with sync_playwright() as p:
            nav = p.chromium.launch(headless=True)
            pg = nav.new_page()
            pg.goto(url, wait_until="networkidle")
            if wait:
                pg.wait_for_selector(wait)
            if scroll:
                pg.mouse.wheel(0, 100000)
                pg.wait_for_timeout(500)
            html = pg.content()
            nav.close()
        self._wait()
        return Page(url=url, html=html, method="browser",
                    elapsed=round(time.perf_counter() - t0, 3))

    def fetch(self, url: str, strategy: str = "auto") -> Page:
        """Obtiene la página. strategy: auto | static | browser.

        'auto' descarga estático y, si la página parece vacía (típico de SPAs
        que rellenan con JS), reintenta con navegador.
        """
        if strategy == "static":
            return self.static(url)
        if strategy == "browser":
            return self.browser(url)
        # auto
        page = self.static(url)
        texto = page.soup.get_text(strip=True)
        if len(texto) < 200:  # heurística: casi sin contenido -> probablemente JS
            return self.browser(url)
        return page

    # --- crawling -----------------------------------------------------------
    def crawl(
        self,
        start: str,
        item: str,
        fields: dict[str, str],
        next: str | None = None,
        pages: int | None = None,
        base: str | None = None,
    ) -> list[dict]:
        """Recorre varias páginas siguiendo el enlace 'next' y extrae 'fields'.

        start:  URL inicial.
        item:   selector de cada registro.
        fields: campos a extraer (ver Page.extract).
        next:   selector del enlace a la siguiente página (ej. "li.next a::attr(href)").
        pages:  límite opcional de páginas.
        base:   prefijo para URLs relativas (si no, se infiere del host).
        """
        from urllib.parse import urljoin

        url = start
        todos: list[dict] = []
        n = 0
        while url:
            page = self.static(url)
            todos.extend(page.extract(item, fields))
            n += 1
            if pages and n >= pages:
                break
            if not next:
                break
            sel, op, arg = _split_selector(next)
            nodo = page.soup.select_one(sel)
            href = _value_from(nodo, op if op != "text" else "attr", arg or "href") if nodo else None
            url = urljoin(base or url, href) if href else None
        return todos

    # --- sesión -------------------------------------------------------------
    def session(self) -> Session:
        return Session(self)

    def _wait(self):
        if self.delay:
            time.sleep(self.delay)
