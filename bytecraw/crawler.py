"""
Crawlers de grafo para ByteCraw: BFS, Shark-Search y OPIC.

La web es un grafo (páginas = nodos, links = aristas). Un crawler decide en
qué ORDEN visitar las URLs con un presupuesto limitado de requests. Cada
estrategia es una respuesta distinta a esa pregunta:

  BFS          — por niveles: primero lo más cercano a la semilla.
  Shark-Search — best-first temático: persigue páginas relevantes a un query
                 (Hersovici et al., 1998). Los links heredan score del padre
                 con decaimiento; las ramas malas se apagan solas.
  OPIC         — On-line Page Importance Computation (Abiteboul et al., 2003):
                 cada página tiene "cash" que reparte a sus links al ser
                 visitada. Es PageRank calculado en vivo, sin el grafo completo.

Uso:

    from bytecraw.crawler import BFS, SharkSearch, OPIC, pagerank

    result = SharkSearch(query="machine learning").crawl(
        "https://example.com", max_pages=100)
    result.pages          # visitadas, en orden
    result.graph          # {url: [links]} para análisis offline
    pagerank(result.graph)
"""

from __future__ import annotations

import heapq
import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urljoin, urlparse

from .core import Scraper

# Extensiones que no son HTML: no vale la pena gastarles un request.
_SKIP_EXT = re.compile(
    r"\.(png|jpe?g|gif|svg|webp|ico|css|js|pdf|zip|gz|tar|mp[34]|avi|mov|woff2?|ttf|xml|rss)$",
    re.IGNORECASE,
)

_WORD = re.compile(r"[a-záéíóúüñ0-9]+", re.IGNORECASE)


def _tokens(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text or "")]


def cosine(text_a: str, text_b: str) -> float:
    """Similitud coseno entre dos textos usando vectores de frecuencia (TF).

    Es la métrica clásica de recuperación de información: 1.0 = mismo
    vocabulario en la misma proporción, 0.0 = ni una palabra en común.
    """
    a, b = Counter(_tokens(text_a)), Counter(_tokens(text_b))
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[w] * b[w] for w in common)
    norm = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return dot / norm if norm else 0.0


def normalize(url: str, base: str) -> str | None:
    """Resuelve relativas, quita #fragmentos y filtra lo que no es página web."""
    absolute, _ = urldefrag(urljoin(base, url))
    parsed = urlparse(absolute)
    if parsed.scheme not in ("http", "https"):
        return None
    if _SKIP_EXT.search(parsed.path):
        return None
    return absolute


class Frontier:
    """Priority queue de URLs pendientes con dedup.

    heapq es un min-heap, así que guardamos -score para sacar siempre la URL
    de MAYOR score. Si una URL se re-encola con score nuevo (pasa en OPIC,
    donde el cash se acumula), usamos "lazy deletion": las entradas viejas se
    descartan al hacer pop comparando contra el score vigente.
    """

    def __init__(self):
        self._heap: list[tuple[float, int, str]] = []
        self._score: dict[str, float] = {}
        self._counter = 0  # desempate FIFO entre scores iguales

    def push(self, url: str, score: float):
        current = self._score.get(url)
        if current is not None and score <= current:
            return
        self._score[url] = score
        self._counter += 1
        heapq.heappush(self._heap, (-score, self._counter, url))

    def pop(self) -> tuple[str, float] | None:
        while self._heap:
            neg, _, url = heapq.heappop(self._heap)
            if url in self._score and -neg == self._score[url]:
                del self._score[url]
                return url, -neg
        return None

    def __contains__(self, url: str) -> bool:
        return url in self._score

    def __len__(self) -> int:
        return len(self._score)


@dataclass
class CrawlResult:
    """Lo que devuelve un crawl: páginas, grafo y números para comparar."""

    strategy: str
    pages: list[dict] = field(default_factory=list)   # url, title, score, relevance, depth, order
    graph: dict[str, list[str]] = field(default_factory=dict)
    stats: dict = field(default_factory=dict)

    def relevant(self, threshold: float = 0.1) -> list[dict]:
        return [p for p in self.pages if p["relevance"] >= threshold]

    def top(self, n: int = 10) -> list[dict]:
        return sorted(self.pages, key=lambda p: p["relevance"], reverse=True)[:n]


class Crawler:
    """Crawler BFS. Las subclases solo cambian CÓMO se puntúan los links.

    El loop es idéntico para todas las estrategias (pop → fetch → extraer
    links → puntuar → push); así la comparación entre estrategias es justa:
    mismo código, distinta función de orden.
    """

    name = "bfs"

    def __init__(self, query: str = "", delay: float = 0.2, timeout: int = 10,
                 same_domain: bool = True):
        self.query = query
        self.same_domain = same_domain
        self.scraper = Scraper(delay=delay, timeout=timeout)

    # --- punto de extensión ---------------------------------------------------
    def score_links(self, url: str, links: list[dict], relevance: float,
                    depth: int) -> list[tuple[str, float]]:
        """BFS: el score solo codifica la profundidad (menos profundo = antes).

        links: [{url, anchor}]. Devuelve [(url, score)] para la frontier.
        """
        return [(l["url"], -(depth + 1)) for l in links]

    def on_visit(self, url: str, links: list[dict]):
        """Hook para estado propio de la estrategia (OPIC reparte cash aquí)."""

    def initial_score(self, url: str) -> float:
        return 0.0

    # --- loop común -------------------------------------------------------------
    def crawl(self, start: str, max_pages: int = 50, max_depth: int = 10) -> CrawlResult:
        start_norm = normalize(start, start)
        if not start_norm:
            raise ValueError(f"URL inválida: {start}")
        domain = urlparse(start_norm).netloc

        frontier = Frontier()
        frontier.push(start_norm, self.initial_score(start_norm))
        visited: set[str] = set()
        depth_of = {start_norm: 0}
        result = CrawlResult(strategy=self.name)
        errors = 0
        t0 = time.perf_counter()

        while len(visited) < max_pages:
            item = frontier.pop()
            if item is None:
                break
            url, score = item
            if url in visited:
                continue
            visited.add(url)
            depth = depth_of.get(url, 0)

            try:
                page = self.scraper.static(url)
            except Exception:
                errors += 1
                continue

            text = page.soup.get_text(" ", strip=True)
            relevance = cosine(text, self.query) if self.query else 0.0
            title = page.css("title") or url

            links = []
            for a in page.soup.select("a[href]"):
                child = normalize(a["href"], url)
                if not child or child == url:
                    continue
                if self.same_domain and urlparse(child).netloc != domain:
                    continue
                links.append({"url": child, "anchor": a.get_text(" ", strip=True)})

            result.graph[url] = [l["url"] for l in links]
            result.pages.append({
                "url": url, "title": title[:120], "score": round(score, 4),
                "relevance": round(relevance, 4), "depth": depth,
                "order": len(result.pages) + 1,
            })

            self.on_visit(url, links)

            if depth < max_depth:
                for child_url, child_score in self.score_links(url, links, relevance, depth):
                    if child_url not in visited:
                        depth_of.setdefault(child_url, depth + 1)
                        frontier.push(child_url, child_score)

        result.stats = {
            "requests": len(visited),
            "errors": errors,
            "elapsed": round(time.perf_counter() - t0, 2),
            "frontier_left": len(frontier),
            "relevant_found": len(result.relevant()) if self.query else None,
            "avg_relevance": round(
                sum(p["relevance"] for p in result.pages) / len(result.pages), 4
            ) if result.pages else 0.0,
        }
        return result


class BFS(Crawler):
    """Alias explícito del comportamiento base."""

    name = "bfs"


class SharkSearch(Crawler):
    """Best-first temático con herencia de score (Hersovici et al., 1998).

    score(link) = γ·heredado + (1−γ)·señal_local
      heredado    = δ·relevancia(padre) si el padre fue relevante,
                    si no δ·heredado(padre)  → las ramas malas decaen δ^n.
      señal_local = coseno(anchor + palabras de la URL, query).
    """

    name = "shark"

    def __init__(self, query: str, delta: float = 0.5, gamma: float = 0.8, **kw):
        super().__init__(query=query, **kw)
        self.delta = delta
        self.gamma = gamma
        self._inherited: dict[str, float] = {}

    def initial_score(self, url: str) -> float:
        self._inherited[url] = 1.0
        return 1.0

    def score_links(self, url, links, relevance, depth):
        # Herencia: si el padre fue relevante, los hijos heredan su relevancia;
        # si no, heredan lo que el padre había heredado. En ambos casos con
        # decaimiento delta: una rama sin señal se apaga como delta^n.
        parent_inherited = self._inherited.get(url, 0.0)
        inherited = self.delta * (relevance if relevance > 0.05 else parent_inherited)
        scored = []
        for l in links:
            url_words = " ".join(_tokens(urlparse(l["url"]).path))
            local = cosine(f'{l["anchor"]} {url_words}', self.query)
            score = self.gamma * inherited + (1 - self.gamma) * local
            self._inherited[l["url"]] = inherited
            scored.append((l["url"], score))
        return scored


class OPIC(Crawler):
    """Importancia estructural online (Abiteboul et al., 2003).

    Cada página tiene cash. Al visitarla: su cash se suma a su historial
    (importancia acumulada), se pone a 0 y se reparte equitativamente entre
    sus links de salida. Se visita siempre la URL con más cash pendiente.
    El total de cash del sistema se conserva (invariante del algoritmo).
    Las páginas sin links de salida (sumideros) devuelven su cash a las URLs
    conocidas no visitadas: el "nodo virtual" del paper, versión inmediata.
    """

    name = "opic"

    def __init__(self, query: str = "", **kw):
        super().__init__(query=query, **kw)
        self.cash: dict[str, float] = {}
        self.history: dict[str, float] = {}
        self._known_unvisited: set[str] = set()
        self._frontier_ref: Frontier | None = None

    def initial_score(self, url: str) -> float:
        self.cash[url] = 1.0
        return 1.0

    def on_visit(self, url: str, links: list[dict]):
        amount = self.cash.pop(url, 0.0)
        self.history[url] = self.history.get(url, 0.0) + amount
        self._known_unvisited.discard(url)
        targets = [l["url"] for l in links] or list(self._known_unvisited)
        if not targets:
            return
        share = amount / len(targets)
        for t in targets:
            self.cash[t] = self.cash.get(t, 0.0) + share
            self._known_unvisited.add(t)

    def score_links(self, url, links, relevance, depth):
        # El cash ya se repartió en on_visit; el score ES el cash acumulado.
        return [(l["url"], self.cash.get(l["url"], 0.0)) for l in links]


def pagerank(graph: dict[str, list[str]], damping: float = 0.85,
             iterations: int = 30) -> dict[str, float]:
    """PageRank por iteración de potencias sobre el grafo crawleado.

    Versión offline del mismo concepto que OPIC aproxima online: comparar
    ambos rankings sobre el mismo grafo es el experimento interesante.
    """
    nodes = set(graph) | {v for vs in graph.values() for v in vs}
    if not nodes:
        return {}
    n = len(nodes)
    rank = {u: 1.0 / n for u in nodes}
    for _ in range(iterations):
        new = {u: (1 - damping) / n for u in nodes}
        for u in nodes:
            out = [v for v in graph.get(u, []) if v in nodes]
            if out:
                share = damping * rank[u] / len(out)
                for v in out:
                    new[v] += share
            else:  # sumidero: reparte a todos (nodo virtual)
                share = damping * rank[u] / n
                for v in nodes:
                    new[v] += share
        rank = new
    return dict(sorted(rank.items(), key=lambda kv: kv[1], reverse=True))
