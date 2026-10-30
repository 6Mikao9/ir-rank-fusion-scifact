"""Run from repository root: python scripts/run_experiment.py.

Tune on 200 deterministically sampled queries from official training qrels;
the official 300-query test set is loaded for evaluation only after tuning.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pathlib
import platform
import random
import statistics
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
import scipy
import sklearn
from rankfusion.core import BM25, TFIDF, evaluate, ranking, rrf, score_fusion


def load_jsonl(path):
    with path.open(encoding='utf-8') as f:
        return {str(x['_id']): x for line in f if (x := json.loads(line))}


def load_qrels(path):
    result = {}
    with path.open(encoding='utf-8', newline='') as f:
        for x in csv.DictReader(f, delimiter='\t'):
            result.setdefault(x['query-id'], {})[x['corpus-id']] = int(x['score'])
    return result


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=pathlib.Path, default=ROOT/'data'/'scifact')
    parser.add_argument('--output', type=pathlib.Path, default=ROOT/'results')
    parser.add_argument('--depth', type=int, default=100)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    corpus = load_jsonl(args.data/'corpus.jsonl')
    queries = load_jsonl(args.data/'queries.jsonl')
    train = load_qrels(args.data/'qrels'/'train.tsv')
    doc_ids = sorted(corpus)
    texts = [corpus[d]['title']+' '+corpus[d]['text'] for d in doc_ids]
    dev_ids = sorted(random.Random(42).sample(sorted(train), min(200, len(train))))
    dev_qrels = {q: train[q] for q in dev_ids}
    retrievers, indexing = {}, {}
    for name, factory in [('bm25', BM25), ('tfidf_word', TFIDF), ('tfidf_char', lambda t: TFIDF(t, char=True))]:
        start = time.perf_counter()
        retrievers[name] = factory(texts)
        indexing[name] = time.perf_counter()-start
        print('Indexed', name, round(indexing[name], 3), flush=True)

    def retrieve(qids):
        runs = {name: {} for name in retrievers}
        latency = {name: [] for name in retrievers}
        for name, retriever in retrievers.items():
            retriever.score(queries[qids[0]]['text'])  # Warm-up excluded.
            for qid in qids:
                start = time.perf_counter()
                run = ranking(retriever.score(queries[qid]['text']), doc_ids, args.depth)
                # Query/document IDs belong to distinct namespaces in SciFact.
                runs[name][qid] = run
                latency[name].append((time.perf_counter()-start)*1000)
        return runs, latency

    dev_runs, _ = retrieve(dev_ids)
    tune_rows = []
    for k in [10, 30, 60, 100]:
        for weight in [0.5, 1.0, 2.0]:
            runs = {q: rrf([dev_runs['bm25'][q], dev_runs['tfidf_word'][q]], k=k, weights=[weight,1]) for q in dev_ids}
            score = evaluate(runs, dev_qrels)[0]['nDCG@10']
            tune_rows.append(dict(method='rrf', k=k, bm25_weight=weight, dev_ndcg10=score))
    best_rrf = max(tune_rows, key=lambda x:x['dev_ndcg10'])
    for alpha in [0.0, 0.25, 0.5, 0.75, 1.0]:
        runs = {q: score_fusion([dev_runs['bm25'][q], dev_runs['tfidf_word'][q]], alpha) for q in dev_ids}
        tune_rows.append(dict(method='score_fusion', alpha=alpha, dev_ndcg10=evaluate(runs, dev_qrels)[0]['nDCG@10']))
    best_score = max((x for x in tune_rows if x['method']=='score_fusion'), key=lambda x:x['dev_ndcg10'])
    dump(args.output/'tuning.json', dict(seed=42, dev_ids=dev_ids, candidates=tune_rows, selected_rrf=best_rrf, selected_score_fusion=best_score))
    # No test qrels are read before all hyperparameters have been frozen above.
    test = load_qrels(args.data/'qrels'/'test.tsv')
    assert not (set(train) & set(test)), 'Train/test query leakage'
    qids = sorted(test)
    runs, latency = retrieve(qids)
    fusions = {
        'rrf_word_k60': lambda q: rrf([runs['bm25'][q], runs['tfidf_word'][q]]),
        'rrf_char_k60': lambda q: rrf([runs['bm25'][q], runs['tfidf_char'][q]]),
        'rrf_all_k60': lambda q: rrf([runs[n][q] for n in retrievers]),
        'rrf_word_tuned': lambda q: rrf([runs['bm25'][q], runs['tfidf_word'][q]], k=best_rrf['k'], weights=[best_rrf['bm25_weight'], 1]),
        'score_fusion_tuned': lambda q: score_fusion([runs['bm25'][q], runs['tfidf_word'][q]], best_score['alpha']),
    }
    fusion_component_ms = {}
    for name, fuse in fusions.items():
        fused, times = {}, []
        for q in qids:
            start = time.perf_counter()
            fused[q] = fuse(q)
            times.append((time.perf_counter()-start)*1000)
        runs[name] = fused
        fusion_component_ms[name] = times
        components = ['bm25','tfidf_word','tfidf_char'] if name=='rrf_all_k60' else ['bm25', 'tfidf_char' if name=='rrf_char_k60' else 'tfidf_word']
        latency[name] = [sum(latency[c][i] for c in components)+times[i] for i in range(len(qids))]
    metrics, all_perquery = {}, []
    for name, run in runs.items():
        aggregate, perquery = evaluate(run, test)
        aggregate.update(mean_query_ms=statistics.mean(latency[name]), p95_query_ms=float(np.percentile(latency[name],95)))
        metrics[name] = aggregate
        for qi, q in enumerate(qids):
            all_perquery.append(dict(method=name, query_id=q, **perquery[q], latency_ms=latency[name][qi]))
        with (args.output/(name+'.trec')).open('w', encoding='utf-8') as f:
            for q in qids:
                for i, (d, score) in enumerate(run[q],1):
                    f.write(f'{q} Q0 {d} {i} {score:.12g} {name}\n')
        print(name, json.dumps(aggregate), flush=True)
    dump(args.output/'metrics.json', metrics)
    with (args.output/'metrics.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['method']+list(next(iter(metrics.values()))))
        writer.writeheader()
        writer.writerows(dict(method=n,**v) for n,v in metrics.items())
    with (args.output/'per_query.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(all_perquery[0]))
        writer.writeheader(); writer.writerows(all_perquery)
    rng = np.random.default_rng(42)
    baseline = {x['query_id']: x['nDCG@10'] for x in all_perquery if x['method']=='bm25'}
    bootstrap = {}
    for name in fusions:
        diff = np.array([x['nDCG@10']-baseline[x['query_id']] for x in all_perquery if x['method']==name])
        samples = diff[rng.integers(0,len(diff),(2000,len(diff)))].mean(axis=1)
        bootstrap[name] = dict(mean_ndcg10_delta=float(diff.mean()), percentile95_ci=[float(x) for x in np.percentile(samples,[2.5,97.5])], wins=int((diff>1e-12).sum()), ties=int((abs(diff)<=1e-12).sum()), losses=int((diff<-1e-12).sum()))
    dump(args.output/'paired_bootstrap.json', dict(seed=42, samples=2000, comparator='bm25', comparisons=bootstrap))
    hashes = {str(f.relative_to(args.data)): hashlib.sha256(f.read_bytes()).hexdigest() for f in [args.data/'corpus.jsonl',args.data/'queries.jsonl',args.data/'qrels'/'train.tsv',args.data/'qrels'/'test.tsv']}
    dump(args.output/'environment.json', dict(python=sys.version, platform=platform.platform(), processor=platform.processor(), numpy=np.__version__, scipy=scipy.__version__, sklearn=sklearn.__version__, corpus_docs=len(corpus), train_queries=len(train), tuning_queries=len(dev_ids), test_queries=len(test), candidate_depth=args.depth, index_seconds=indexing, dataset_sha256=hashes, timing_note='CPU single-query retrieval after one warm-up. Indexing excluded. Fusion latency is sequential sum of separately timed base retrievals plus fusion; no parallel retrieval is assumed.', bm25=dict(k1=1.2,b=0.75,tokenizer='unicode word length >=2, lowercase, no stemming or stopwords'), tfidf_word='sublinear tf, smooth idf, L2 cosine', tfidf_char='char_wb 3-5 grams, min_df2, max_features100000, sublinear tf, smooth idf, L2 cosine'))


if __name__=='__main__':
    main()
