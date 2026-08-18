"""
Minimal in-memory text search.

Vendored from https://github.com/alexeygrigorev/minsearch
(same approach as the original fitness-assistant reference project).

Index documents with TF-IDF over multiple text fields, filter by exact
keyword fields, and score with cosine similarity + per-field boosts.
"""

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class Index:
    """In-memory keyword search index.

    Attributes:
        text_fields (list): fields indexed with TF-IDF.
        keyword_fields (list): fields used for exact-match filtering.
    """

    def __init__(self, text_fields, keyword_fields, vectorizer_params=None):
        if vectorizer_params is None:
            # allow single-character tokens so numeric section labels
            # like "2.1.1" still produce a vocabulary
            vectorizer_params = {"token_pattern": r"(?u)\b\w+\b"}
        self.text_fields = text_fields
        self.keyword_fields = keyword_fields

        self.vectorizers = {
            field: TfidfVectorizer(**vectorizer_params) for field in text_fields
        }
        self.keyword_df = None
        self.text_matrices = {}
        self.docs = []

    def fit(self, docs):
        """Index the given list of dicts."""
        self.docs = docs
        keyword_data = {field: [] for field in self.keyword_fields}

        for field in self.text_fields:
            texts = [str(doc.get(field, "")) for doc in docs]
            try:
                self.text_matrices[field] = self.vectorizers[field].fit_transform(texts)
            except ValueError:
                # field has no usable tokens (e.g. all stop words); skip it
                self.text_matrices[field] = None

        for doc in docs:
            for field in self.keyword_fields:
                keyword_data[field].append(doc.get(field, ""))

        self.keyword_df = pd.DataFrame(keyword_data)
        return self

    def search(self, query, filter_dict=None, boost_dict=None, num_results=10):
        """Search the index.

        Args:
            query (str): the search query.
            filter_dict (dict): exact-match filters on keyword fields.
            boost_dict (dict): per-field score multipliers.
            num_results (int): number of results to return.

        Returns:
            list of matching documents, best first.
        """
        if filter_dict is None:
            filter_dict = {}
        if boost_dict is None:
            boost_dict = {}

        scores = np.zeros(len(self.docs))

        for field in self.text_fields:
            if self.text_matrices[field] is None:
                continue
            query_vec = self.vectorizers[field].transform([query])
            sim = cosine_similarity(query_vec, self.text_matrices[field]).flatten()
            boost = boost_dict.get(field, 1)
            scores += sim * boost

        for field, value in filter_dict.items():
            if field in self.keyword_fields:
                mask = (self.keyword_df[field] == value).to_numpy()
                scores = scores * mask

        top_indices = np.argpartition(scores, -num_results)[-num_results:]
        top_indices = top_indices[np.argsort(-scores[top_indices])]

        return [self.docs[i] for i in top_indices if scores[i] > 0]
