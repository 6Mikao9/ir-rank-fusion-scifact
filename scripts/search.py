"""Interactive demo: python scripts/search.py "vitamin D bone density"."""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from rankfusion.core import BM25, TFIDF, ranking, rrf

parser = argparse.ArgumentParser()
parser.add_argument('query', help='English biomedical claim or keywords')
parser.add_argument('--top-k', type=int, default=5)
parser.add_argument('--method', choices=['bm25', 'rrf_word', 'rrf_char'], default='rrf_char')
args = parser.parse_args()
with (ROOT / 'data/scifact/corpus.jsonl').open(encoding='utf-8') as f:
    corpus = {str(x['_id']): x for line in f if (x := json.loads(line))}
ids = sorted(corpus)
texts = [corpus[d]['title']+' '+corpus[d]['text'] for d in ids]
bm25 = BM25(texts)
base = ranking(bm25.score(args.query), ids, 100)
if args.method == 'bm25':
    result = base[:args.top_k]
else:
    tfidf = TFIDF(texts, char=args.method == 'rrf_char')
    result = rrf([base, ranking(tfidf.score(args.query), ids, 100)], limit=args.top_k)
print(f'Method: {args.method}. Candidate evidence only; no support/refute verdict.\n')
for i,(doc,score) in enumerate(result,1):
    print(f'{i}. [{doc}] score={score:.6f}\n{corpus[doc]["title"]}\n{corpus[doc]["text"][:600]}\n')
