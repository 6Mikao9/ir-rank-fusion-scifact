"""Generate LaTeX tables/macros and optional figures from measured results."""
import json
import pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
out=ROOT/'results'
m=json.loads((out/'metrics.json').read_text(encoding='utf-8'))
b=json.loads((out/'paired_bootstrap.json').read_text(encoding='utf-8'))['comparisons']
labels={
 'bm25':'BM25','tfidf_word':'Word TF--IDF','tfidf_char':'Char TF--IDF',
 'rrf_word_k60':'RRF word ($k=60$)','rrf_char_k60':'RRF char ($k=60$)',
 'rrf_all_k60':'RRF all ($k=60$)','rrf_word_tuned':'Weighted RRF (dev)',
 'score_fusion_tuned':'Score fusion (dev)',
}
lines=[r'\begin{tabular}{lrrrrr}',r'\toprule',r'Method & nDCG@10 & MAP@100 & MRR@10 & R@100 & ms/query \\',r'\midrule']
for name,v in m.items():
    lines.append(labels[name]+' & '+' & '.join(f'{v[k]:.4f}' for k in ['nDCG@10','MAP@100','MRR@10','Recall@100'])+f' & {v["mean_query_ms"]:.2f} '+r'\\')
lines += [r'\bottomrule',r'\end{tabular}']
(out/'generated_metrics.tex').write_text('\n'.join(lines)+'\n',encoding='utf-8')
vals={
 'BaseNDCG':m['bm25']['nDCG@10'],'FusionNDCG':m['rrf_char_k60']['nDCG@10'],
 'BaseRecall':m['bm25']['Recall@100'],'FusionRecall':m['rrf_char_k60']['Recall@100'],
 'FusionDelta':b['rrf_char_k60']['mean_ndcg10_delta'],
 'FusionCILow':b['rrf_char_k60']['percentile95_ci'][0],
 'FusionCIHigh':b['rrf_char_k60']['percentile95_ci'][1],
 'BaseMs':m['bm25']['mean_query_ms'],'FusionMs':m['rrf_char_k60']['mean_query_ms'],
}
(out/'generated_summary.tex').write_text('\n'.join('\\newcommand{\\'+k+'}{'+f'{v:.4f}'+'}' for k,v in vals.items())+'\n',encoding='utf-8')
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figdir=out/'figures';figdir.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig,ax=plt.subplots(figsize=(7,4),layout='constrained')
    offsets={'bm25':(5,-16),'tfidf_word':(5,4),'tfidf_char':(5,-15),'rrf_word_k60':(5,-13),'rrf_char_k60':(5,4),'rrf_all_k60':(5,-15),'rrf_word_tuned':(5,4),'score_fusion_tuned':(75,0)}
    short={'bm25':'BM25','tfidf_word':'Word TF-IDF','tfidf_char':'Char TF-IDF','rrf_word_k60':'RRF word','rrf_char_k60':'RRF char','rrf_all_k60':'RRF all','rrf_word_tuned':'Weighted RRF','score_fusion_tuned':'Score fusion'}
    for name,v in m.items():
        ax.scatter(v['mean_query_ms'],v['nDCG@10'],s=40)
        ax.annotate(short[name],(v['mean_query_ms'],v['nDCG@10']),xytext=offsets[name],textcoords='offset points',fontsize=8)
    ax.set(xlabel='Mean CPU query latency (ms, sequential fusion)',ylabel='nDCG@10',title='SciFact: retrieval quality and measured CPU latency',xlim=(0,70),ylim=(.615,.68))
    ax.grid(alpha=.2)
    fig.savefig(figdir/'quality_latency.png',dpi=220)
    plt.close(fig)
    names=list(b)
    fig,ax=plt.subplots(figsize=(7,3.5),layout='constrained')
    for i,n in enumerate(names):
        mean=b[n]['mean_ndcg10_delta'];lo,hi=b[n]['percentile95_ci']
        ax.errorbar(mean,i,xerr=[[mean-lo],[hi-mean]],fmt='o',capsize=4,color='#17658b')
    ax.axvline(0,color='grey',linestyle='--',linewidth=1)
    ax.set_yticks(range(len(names)),[short[n] for n in names])
    ax.set(xlabel='Paired nDCG@10 difference vs. BM25 (95% bootstrap CI)',title='All estimated gain intervals include zero')
    ax.grid(axis='x',alpha=.2)
    fig.savefig(figdir/'bootstrap_delta.png',dpi=220)
    plt.close(fig)
except ImportError:
    print('matplotlib not installed; LaTeX table/macros generated without figures.')
print('Report assets exported.')
