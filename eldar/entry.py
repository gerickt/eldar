import re
from collections import defaultdict
from dataclasses import dataclass

from .regex import WILD_CARD_REGEX


class Entry:
    def __init__(self, query):
        self.not_ = False

        if query[:4] == "not ":
            self.not_ = True
            query = query[4:]

        self.query = strip_quotes(query)

        if "*" in self.query:
            self.pattern = self.query.replace("*", WILD_CARD_REGEX)
            self.rgx = re.compile(self.pattern)
        else:
            self.rgx = None

    def evaluate(self, doc):
        if self.rgx:

            if isinstance(doc, str):
                doc = [doc]

            for item in doc:
                if self.rgx.match(item):
                    res = True
                    break
            else:
                res = False
        else:
            res = self.query in doc

        if self.not_:
            return not res

        return res

    def search(self, index):
        if self.rgx:
            # Si hay comodines, buscamos todos los términos que coincidan con el patrón
            matching_terms = [
                term for term in index._index.keys() if self.rgx.match(term)
            ]
            result_ids = set()
            for term in matching_terms:
                items = index._index.get(term, set())
                result_ids.update([item.id for item in items])
            return result_ids
        else:
            # Búsqueda exacta del término
            items = index._index.get(self.query, set())
            result_ids = set([item.id for item in items])
            return result_ids

    def __repr__(self):
        if self.not_:
            return f'NOT "{self.query}"'
        return f'"{self.query}"'


class IndexEntry:
    def __init__(self, query_term):
        self.not_ = False

        if query_term == "*":
            raise ValueError("Single character wildcards * are not implemented")

        query_term = strip_quotes(query_term)
        if " " in query_term:  # multiword query
            self.query_term = query_term.split()
            self.search = self.search_multiword
        else:
            self.query_term = query_term
            self.search = self.search_simple

    def search_simple(self, index):
        res = index.get(self.query_term)
        return {match.id for match in res}

    def search_multiword(self, index):
        docs = defaultdict(list)
        for token in self.query_term:
            items = index.get(token)
            for item in items:
                docs[item.id].append((item.position, token))

        # utils variable
        first_token = self.query_term[0]
        query_len = len(self.query_term)
        query_rest = self.query_term[1:]
        iter_rest = range(1, query_len)

        results = set()
        for doc_id, tokens in docs.items():
            tokens = sorted(tokens)
            if len(tokens) < query_len:
                continue
            for i in range(len(tokens) - query_len + 1):
                pos, tok = tokens[i]
                if tok != first_token:
                    continue
                is_a_match = True
                for j, correct_token in zip(iter_rest, query_rest):
                    next_pos, next_tok = tokens[i + j]
                    if correct_token != next_tok or next_pos != pos + j:
                        is_a_match = False
                        break
                if is_a_match:
                    results.add(doc_id)
                    break
        return results

    def __repr__(self):
        if self.not_:
            return f'NOT "{self.query_term}"'
        return f'"{self.query_term}"'


class ProximityEntry:
    def __init__(self, left, right, distance):
        self.left = left
        self.right = right
        self.distance = distance

    def evaluate(self, doc):
        # Tokenizar el documento manteniendo las posiciones
        tokens = doc.split()
        positions_left = [
            i for i, token in enumerate(tokens) if self.left.evaluate(token)
        ]
        positions_right = [
            i for i, token in enumerate(tokens) if self.right.evaluate(token)
        ]

        # Verificar si alguna pareja de posiciones cumple con la distancia
        for pos_left in positions_left:
            for pos_right in positions_right:
                if abs(pos_left - pos_right) <= self.distance:
                    return True
        return False

    def search(self, index):
        # Obtener los items para los términos izquierdo y derecho
        left_items = index._index.get(self.left.query, set())
        right_items = index._index.get(self.right.query, set())

        # Crear diccionarios para mapear IDs de documentos a posiciones
        left_positions = defaultdict(list)
        for item in left_items:
            left_positions[item.id].append(item.position)

        right_positions = defaultdict(list)
        for item in right_items:
            right_positions[item.id].append(item.position)

        result_ids = set()

        # Encontrar documentos que contengan ambos términos a la distancia especificada
        common_doc_ids = set(left_positions.keys()) & set(right_positions.keys())
        for doc_id in common_doc_ids:
            left_pos = left_positions[doc_id]
            right_pos = right_positions[doc_id]
            for lp in left_pos:
                for rp in right_pos:
                    if abs(lp - rp) <= self.distance:
                        result_ids.add(doc_id)
                        break  # Ya encontramos una coincidencia en este documento
                else:
                    continue
                break

        return result_ids

    def __repr__(self):
        return f"({self.left}) /{self.distance} ({self.right})"


def strip_quotes(query):
    if query[0] == '"' and query[-1] == '"':
        return query[1:-1]
    return query


@dataclass(unsafe_hash=True, order=True)
class Item:
    id: int
    position: int
