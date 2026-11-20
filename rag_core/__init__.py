"""Retrieval core shared by the local P0 path (app.api) and the enterprise path (app.enterprise).

Keeping chunking, sparse scoring, fusion and reranking in one place means the
evaluation in ``eval/run_cnooc_eval.py`` measures the same algorithm both
entry points run.
"""
