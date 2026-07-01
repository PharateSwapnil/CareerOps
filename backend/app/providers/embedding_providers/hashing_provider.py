"""A local, dependency-free embedding provider using the "hashing trick"
(feature hashing) over word tokens - the same technique behind scikit-learn's
HashingVectorizer. Every request runs entirely in-process with no network
call and no API key, so semantic search works out of the box.

IMPORTANT HONESTY NOTE: this captures lexical/n-gram term overlap, not true
neural semantic meaning. It will find jobs that share vocabulary with a
query, but it won't reliably generalize across terminology the way a trained
embedding model does - e.g. it won't connect a "Snowflake/Databricks/PySpark"
query to an "Analytics Engineer" posting unless those words literally
co-occur somewhere in the text. That cross-terminology generalization (the
example used in this project's original spec) needs a real neural embedding
model - see VoyageEmbeddingProvider for that. This provider exists so the
feature works immediately with zero setup, with a documented upgrade path.
"""
import hashlib
import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#.\-]*")

# Common English stopwords that add noise to lexical overlap without
# carrying meaning - filtering them measurably improves match quality for
# a bag-of-words approach.
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "this", "that", "as", "it", "we", "you", "your", "our", "will", "have",
    "has", "not", "who", "their", "they", "which", "into", "about", "such",
}


class HashingEmbeddingProvider:
    name = "hashing"
    model = "hashing-v1"
    dimension = 512

    async def embed(self, texts: list[str], input_type: str = "document") -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        tokens = [
            t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS and len(t) > 1
        ]
        if not tokens:
            return [0.0] * self.dimension

        counts = Counter(tokens)
        vector = [0.0] * self.dimension

        for token, count in counts.items():
            digest = hashlib.md5(token.encode("utf-8")).hexdigest()
            bucket = int(digest[:8], 16) % self.dimension
            # Use another bit of the hash as a sign to reduce systematic
            # collision bias, per the standard feature-hashing trick.
            sign = 1.0 if int(digest[8], 16) % 2 == 0 else -1.0
            # log-scaled term frequency keeps very common in-doc words
            # (e.g. "engineer" repeated many times) from dominating.
            vector[bucket] += sign * (1.0 + math.log(count))

        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector
