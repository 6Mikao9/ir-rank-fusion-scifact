"""Retrievers and evaluation. Rankings are lists of (document ID, score).

nDCG uses linear relevance gain, matching trec_eval ndcg_cut. AP@100 uses
total_relevant as denominator, matching trec_eval map_cut.
All reported SciFact judgments are binary. Unjudged documents count as 0.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer


def tokenize(text):
    return re.findall(r"(?u)\b\w\w+\b", text.lower())


def ranking(scores, doc_ids, limit=100):
    """Positive matches only. Stable ties use lexicographic document ID."""
    candidates = np.flatnonzero(scores > 0)
    order = sorted(candidates, key=lambda i: (-float(scores[i]), doc_ids[i]))[:limit]
    return [(doc_ids[i], float(scores[i])) for i in order]


class BM25:
    """Robertson BM25 with positive log(1+(N-df+.5)/(df+.5)) IDF.

    Repeated query terms contribute repeatedly (no separate query saturation).
    This is a transparent lexical baseline, not Elasticsearch's BEIR baseline.
    """
    def __init__(self, texts, k1=1.2, b=0.75):
        self.vectorizer = CountVectorizer(analyzer=tokenize, dtype=np.float64)
        counts = self.vectorizer.fit_transform(texts).tocsc()
        lengths = np.asarray(counts.sum(axis=1)).ravel()
        avg = lengths.mean()
        self.idf = np.log1p((len(texts) - np.diff(counts.indptr) + 0.5) / (np.diff(counts.indptr) + 0.5))
        coo = counts.tocoo()
        weights = coo.data * (k1 + 1) / (coo.data + k1 * (1 - b + b * lengths[coo.row] / avg))
        self.matrix = sparse.csr_matrix((weights, (coo.row, coo.col)), shape=counts.shape)

    def score(self, query):
        q = self.vectorizer.transform([query]).multiply(self.idf)
        return (self.matrix @ q.T).toarray().ravel()


class TFIDF:
    def __init__(self, texts, char=False):
        args = dict(dtype=np.float32, norm='l2', sublinear_tf=True, smooth_idf=True)
        if char:
            args.update(analyzer='char_wb', ngram_range=(3, 5), min_df=2, max_features=100000)
        else:
            args.update(analyzer=tokenize)
        self.vectorizer = TfidfVectorizer(**args)
        self.matrix = self.vectorizer.fit_transform(texts)

    def score(self, query):
        return (self.matrix @ self.vectorizer.transform([query]).T).toarray().ravel()


def rrf(runs, k=60, weights=None, limit=100):
    if k < 0:
        raise ValueError('k must be nonnegative')
    weights = [1.0] * len(runs) if weights is None else weights
    if len(weights) != len(runs) or any(w < 0 for w in weights):
        raise ValueError('Expected one nonnegative weight per run')
    scores = defaultdict(float)
    for run, weight in zip(runs, weights):
        seen = set()
        for rank, (doc, _) in enumerate(run, 1):
            if doc in seen:
                raise ValueError('Duplicate document in ranking')
            seen.add(doc)
            scores[doc] += weight / (k + rank)
    return sorted(((d, s) for d, s in scores.items() if s > 0), key=lambda x: (-x[1], x[0]))[:limit]


def score_fusion(runs, alpha=0.5, limit=100):
    """Min-max normalize each truncated input run; absent docs contribute 0."""
    scores = defaultdict(float)
    for run, weight in zip(runs, [alpha, 1-alpha]):
        if not run:
            continue
        values = [s for _, s in run]
        lo, hi = min(values), max(values)
        for doc, score in run:
            norm = (score-lo)/(hi-lo) if hi > lo else 1.0
            scores[doc] += weight * norm
    return sorted(((d, s) for d, s in scores.items() if s > 0), key=lambda x: (-x[1], x[0]))[:limit]


def evaluate_query(run, qrels):
    relevant = {d for d, r in qrels.items() if r > 0}
    ranked = [d for d, _ in run]
    ideal = sorted((r for r in qrels.values() if r > 0), reverse=True)[:10]
    dcg = sum(qrels.get(d, 0)/math.log2(i+2) for i, d in enumerate(ranked[:10]))
    idcg = sum(r/math.log2(i+2) for i, r in enumerate(ideal))
    hits = 0
    ap = 0.0
    for i, doc in enumerate(ranked[:100], 1):
        if doc in relevant:
            hits += 1
            ap += hits/i
    return {
        'nDCG@10': dcg/idcg if idcg else 0.0,
        'MAP@100': ap/len(relevant) if relevant else 0.0,
        'MRR@10': next((1/i for i, d in enumerate(ranked[:10], 1) if d in relevant), 0.0),
        'Recall@100': hits/len(relevant) if relevant else 0.0,
    }


def evaluate(runs, qrels):
    per_query = {qid: evaluate_query(runs.get(qid, []), rels) for qid, rels in qrels.items()}
    mean = {metric: float(np.mean([v[metric] for v in per_query.values()])) for metric in ['nDCG@10', 'MAP@100', 'MRR@10', 'Recall@100']}
    return mean, per_query
