import math
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'src'))
from rankfusion.core import BM25, TFIDF, evaluate_query, ranking, rrf, score_fusion


class RetrievalTests(unittest.TestCase):
    def test_metrics_hand_calculated(self):
        m=evaluate_query([('x',3),('a',2),('b',1)],{'a':1,'b':1})
        expected=(1/math.log2(3)+1/math.log2(4))/(1+1/math.log2(3))
        self.assertAlmostEqual(m['nDCG@10'],expected)
        self.assertAlmostEqual(m['MAP@100'],(1/2+2/3)/2)
        self.assertEqual(m['MRR@10'],.5)
        self.assertEqual(m['Recall@100'],1)

    def test_missing_and_empty(self):
        self.assertEqual(evaluate_query([],{'a':1})['nDCG@10'],0)
        self.assertEqual(evaluate_query([('x',1)],{})['MAP@100'],0)

    def test_trec_ap_cutoff_denominator(self):
        # trec_eval map_cut averages over all relevant docs, including beyond cutoff.
        qrels={str(i):1 for i in range(101)}
        run=[(str(i),101-i) for i in range(100)]
        self.assertAlmostEqual(evaluate_query(run,qrels)['MAP@100'],100/101)

    def test_rrf_ties_and_scores(self):
        run=rrf([[('b',99),('a',1)],[('a',.3),('b',.2)]])
        self.assertEqual([d for d,_ in run],['a','b'])
        self.assertAlmostEqual(run[0][1],1/61+1/62)
        self.assertEqual(rrf([[('b',1)],[('a',100)]],weights=[0,1])[0][0],'a')
        with self.assertRaises(ValueError):rrf([[('a',1),('a',.5)]])

    def test_positive_only_and_no_lexical_match(self):
        docs=['apple banana fruit','galaxy star space','apple orchard fruit']
        for retriever in [BM25(docs),TFIDF(docs)]:
            run=ranking(retriever.score('apple'),['a','b','c'])
            self.assertEqual({d for d,_ in run},{'a','c'})
            self.assertEqual(ranking(retriever.score('zzzzzz'),['a','b','c']),[])

    def test_score_fusion(self):
        run=score_fusion([[('a',10),('b',5)],[('b',.9),('a',.1)]],.5)
        self.assertEqual([d for d,_ in run],['a','b'])
        self.assertEqual(run[0][1],.5)


if __name__=='__main__':unittest.main()
