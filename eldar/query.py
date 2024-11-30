from unidecode import unidecode
from lark import Lark, Transformer, Token
from .entry import Entry, ProximityEntry
from .operators import AND, OR, NOT, ANDNOT
import re
from .regex import WORD_REGEX

grammar = r"""
%import common.NUMBER
%import common.WS_INLINE
%ignore WS_INLINE

%left OR
%left AND
%left NOT
%left PROX

?start: expr

?expr: expr OR expr           -> or_op
     | expr AND expr          -> and_op
     | expr NOT expr          -> and_not_op
     | term

?term: NOT term               -> not_op
     | term PROX term         -> proximity_op
     | QUOTED_STRING          -> quoted_term
     | WORD                   -> word_term
     | "(" expr ")"           -> group

AND: /AND/i
OR: /OR/i
NOT: "-"
PROX: "/" NUMBER

WORD: /[^()\s"\/-]+/
QUOTED_STRING: "\"" /.*?(?<!\\)"/
"""


class QueryTransformer(Transformer):
    def __init__(self, ignore_case=True, ignore_accent=True):
        super().__init__()
        self.ignore_case = ignore_case
        self.ignore_accent = ignore_accent

    def start(self, args):
        return args[0]

    def expr(self, args):
        return args[0]

    def or_op(self, args):
        left, right = args
        return OR(left, right)

    def and_op(self, args):
        left, right = args
        return AND(left, right)

    def and_not_op(self, args):
        left, right = args
        return ANDNOT(left, right)

    def not_op(self, args):
        expr = args[0]
        return NOT(expr)

    def proximity_op(self, args):
        left, right = args
        return ProximityEntry(left, right, distance=self.current_prox_distance)

    def PROX(self, token):
        self.current_prox_distance = int(token[1:])
        return token

    def word_term(self, args):
        word = args[0]
        return Entry(word)

    def quoted_term(self, args):
        phrase = args[0][1:-1]
        return Entry(phrase)

    def group(self, args):
        return args[0]

    def NUMBER(self, token):
        return int(token)

    def WORD(self, token):
        word = str(token)
        if self.ignore_case:
            word = word.lower()
        if self.ignore_accent:
            word = unidecode(word)
        return word

    def QUOTED_STRING(self, token):
        text = str(token)
        if self.ignore_case:
            text = text.lower()
        if self.ignore_accent:
            text = unidecode(text)
        return text


def parse_main_query(query_str, ignore_case=True, ignore_accent=True):
    parser = Lark(grammar, start="start", parser="lalr")
    transformer = QueryTransformer(ignore_case=ignore_case, ignore_accent=ignore_accent)
    tree = parser.parse(query_str)
    query_obj = transformer.transform(tree)
    return query_obj


def parse_query(query, ignore_case=True, ignore_accent=True):
    if ignore_accent:
        query = unidecode(query)
    return parse_main_query(query, ignore_case, ignore_accent)


class Query:
    def __init__(self, query, ignore_case=True, ignore_accent=True, match_word=True):
        self.ignore_case = ignore_case
        self.ignore_accent = ignore_accent
        self.match_word = match_word
        self.query = parse_query(query, ignore_case, ignore_accent)

    def preprocess(self, doc):
        if self.ignore_case:
            doc = doc.lower()
        if self.ignore_accent:
            doc = unidecode(doc)
        if self.match_word:
            doc = set(re.findall(WORD_REGEX, doc, re.UNICODE))
        return doc

    def evaluate(self, doc):
        doc = self.preprocess(doc)
        return self.query.evaluate(doc)

    def filter(self, documents):
        docs = []
        for doc in documents:
            if not self.evaluate(doc):
                continue
            docs.append(doc)
        return docs

    def __call__(self, doc):
        return self.evaluate(doc)

    def __repr__(self):
        return self.query.__repr__()
