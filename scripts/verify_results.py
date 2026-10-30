"""Verify result artifacts independently from indexing and export case studies."""
import csv
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rankfusion.core import evaluate

data=ROOT/'data/scifact'
out=ROOT/'results'
qrels={}
with (data/'qrels/test.tsv').open(encoding='utf-8') as f:
    for row in csv.DictReader(f,delimiter='\t'):
        qrels.setdefault(row['query-id'],{})[row['corpus-id']]=int(row['score'])
metrics=json.loads((out/'metrics.json').read_text(encoding='utf-8'))
runs={}
for name in metrics:
    runs[name]={}
    with (out/(name+'.trec')).open(encoding='utf-8') as f:
        for line in f:
            qid,_,doc,rank,score,tag=line.split()
            assert tag==name
            current=runs[name].setdefault(qid,[])
            assert int(rank)==len(current)+1
            assert doc not in {d for d,_ in current}
            current.append((doc,float(score)))
    assert set(runs[name])==set(qrels)
    recomputed=evaluate(runs[name],qrels)[0]
    for key,value in recomputed.items():
        assert abs(value-metrics[name][key])<1e-12,(name,key,value,metrics[name][key])
with (data/'queries.jsonl').open(encoding='utf-8') as f:
    queries={str(x['_id']):x['text'] for line in f if (x:=json.loads(line))}
with (data/'corpus.jsonl').open(encoding='utf-8') as f:
    docs={str(x['_id']):x for line in f if (x:=json.loads(line))}
base=evaluate(runs['bm25'],qrels)[1]
fused=evaluate(runs['rrf_char_k60'],qrels)[1]
deltas=sorted(qrels,key=lambda q:(fused[q]['nDCG@10']-base[q]['nDCG@10'],q))
cases=[]
for label,qs in [('largest_losses',deltas[:3]),('largest_gains',deltas[-3:][::-1])]:
    for q in qs:
        cases.append(dict(category=label,query_id=q,query=queries[q],relevant_documents=[dict(id=d,title=docs[d]['title']) for d,r in qrels[q].items() if r>0],bm25_ndcg10=base[q]['nDCG@10'],rrf_char_ndcg10=fused[q]['nDCG@10'],rankings={n:[dict(id=d,score=s,title=docs[d]['title']) for d,s in runs[n][q][:5]] for n in ['bm25','tfidf_char','rrf_char_k60']}))
(out/'case_studies.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'Verified {len(metrics)} methods x {len(qrels)} test queries. Exported 6 case studies.')
