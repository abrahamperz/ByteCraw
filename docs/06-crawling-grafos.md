# 6 · Crawling de grafos (avanzado)

La web es un grafo: páginas = nodos, links = aristas. Un crawler decide en qué
**orden** visitar las URLs con un presupuesto limitado de requests. ByteCraw trae
tres estrategias con el mismo loop y distinto algoritmo de orden:

| Estrategia | Idea | Optimiza |
|---|---|---|
| `BFS` | recorre por niveles desde la semilla | cobertura cercana |
| `SharkSearch` | best-first temático: los links heredan score de padres relevantes con decaimiento δ (Hersovici et al., 1998) | relevancia a un tema |
| `OPIC` | cada página tiene "cash" que reparte a sus links al ser visitada; es PageRank calculado en vivo (Abiteboul et al., 2003) | importancia estructural |

```python
from bytecraw.crawler import BFS, SharkSearch, OPIC, pagerank

result = SharkSearch(query="machine learning").crawl(
    "https://example.com", max_pages=100)

result.pages           # visitadas en orden, con relevancia coseno de cada una
result.relevant(0.2)   # solo las que superan el umbral
result.stats           # requests, relevantes encontradas, relevancia promedio

pagerank(result.graph) # PageRank offline sobre el grafo crawleado
```

La relevancia se mide con similitud coseno TF (implementada en la librería, sin
dependencias). Pruébalas en vivo y compáralas en
[byte-craw.vercel.app/methods](https://byte-craw.vercel.app/methods#advanced).

---

[← Volver al índice](../README.md) · [Siguiente: Markdown para LLMs →](markdown-llms.md)
