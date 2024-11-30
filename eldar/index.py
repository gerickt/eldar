import re
from collections import defaultdict

from unidecode import unidecode
import logging

from .entry import IndexEntry, Item
from .query import parse_main_query, parse_query, QueryTransformer
from .regex import WORD_REGEX

PUNCTUATION = """'!#$%&\'()+,-./:;<=>?@[\\]^_`{|}~'"""


class Index:
    def __init__(
        self,
        ignore_case=True,
        ignore_accent=True,
        ignore_punctuation=True,
        use_trie=True,
    ):
        self.ignore_case = ignore_case
        self.ignore_accent = ignore_accent
        self.ignore_punctuation = ignore_punctuation
        self.use_trie = use_trie
        self._index = defaultdict(set)
        self._is_dataframe = False
        self._columns = []

    def get(self, query_term):
        if query_term == "*":
            raise ValueError("Single character wildcards * are not implemented")

        if self.ignore_punctuation:
            query_term = query_term.translate(str.maketrans("", "", PUNCTUATION))

        if "*" not in query_term:
            res = self._index.get(query_term, set())
            if not isinstance(res, set):
                res = set(res)
            return res
        else:
            query_regex = query_term.replace("*", ".*")
            if self.use_trie:
                matches = self._trie.get(query_term)
                matches = [
                    token
                    for token in matches
                    if re.match(query_regex, token) is not None
                ]
            else:
                matches = [
                    token
                    for token in self._index
                    if re.match(query_regex, token) is not None
                ]
            results = set()
            for match in matches:
                res = self._index[match]
                if not isinstance(res, set):
                    res = set(res)
                results.update(res)
            return results

    def build(self, documents, column=None, verbose=False):
        if isinstance(documents, list):
            self.documents = documents
            if verbose:
                from tqdm import tqdm

                iteration = tqdm(enumerate(documents), total=len(documents))
            else:
                iteration = enumerate(documents)

        else:
            import pandas as pd

            assert isinstance(documents, pd.DataFrame)
            assert column is not None
            assert list(documents.index) == list(range(len(documents)))

            self.documents = documents
            self._columns = documents.columns
            self._is_dataframe = True

            if verbose:
                from tqdm import tqdm

                iteration = tqdm(enumerate(documents[column]), total=len(documents))
            else:
                iteration = enumerate(documents[column])

        for i, document in iteration:
            tokens = self.preprocess(document)
            for j, token in enumerate(tokens):
                if self.ignore_punctuation:
                    token = token.translate(str.maketrans("", "", PUNCTUATION))
                self._index[token].add(Item(i, j))

        if self.use_trie:
            from .trie import Trie

            self._trie = Trie()
            self._trie.add_tokens(self._index.keys())

    def preprocess(self, doc):
        if self.ignore_case:
            doc = doc.lower()
        if self.ignore_accent:
            doc = unidecode(doc)
        doc = re.findall(WORD_REGEX, doc, re.UNICODE)
        return doc

    def search(self, query, return_ids=False):
        # Add logging
        logging.debug(f"Input query: {query}")

        # Parse the query string into a parse tree
        parse_tree = parse_query(
            query, ignore_case=self.ignore_case, ignore_accent=self.ignore_accent
        )
        logging.debug(f"Parse tree: {parse_tree}")

        try:
            # Transform parse tree into executable query object
            transformer = QueryTransformer()
            query_obj = transformer.transform(parse_tree)
            logging.debug(f"Transformed query: {query_obj}")

            # Execute the search on the transformed query object
            ids = query_obj.search(self)

            if return_ids:
                return ids
            if not self._is_dataframe:
                return [self.documents[i] for i in ids]
            return self.documents.iloc[list(ids)]

        except Exception as e:
            logging.error(f"Search failed: {str(e)}")
            raise RuntimeError(f"Search operation failed: {str(e)}") from e

    def count(self, query):
        return len(self.search(query, return_ids=True))

    def save(self, filename):
        import pickle

        with open(filename, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(filename):
        import pickle

        with open(filename, "rb") as f:
            index = pickle.load(f)
        return index

    def gui(self):
        from .gui import create_app

        create_app(self)
