class Binary:
    def __init__(self, left, right):
        self.left = left
        self.right = right


class Unary:
    def __init__(self, expr):
        self.expr = expr


class AND(Binary):
    def evaluate(self, doc):
        return self.left.evaluate(doc) and self.right.evaluate(doc)

    def search(self, index):
        left_ids = self.left.search(index)
        right_ids = self.right.search(index)
        return left_ids & right_ids

    def __repr__(self):
        return f"({self.left}) AND ({self.right})"


class OR(Binary):
    def evaluate(self, doc):
        return self.left.evaluate(doc) or self.right.evaluate(doc)

    def search(self, index):
        left_ids = self.left.search(index)
        right_ids = self.right.search(index)
        return left_ids | right_ids

    def __repr__(self):
        return f"({self.left}) OR ({self.right})"


class NOT(Unary):
    def evaluate(self, doc):
        return not self.expr.evaluate(doc)

    def search(self, index):
        all_ids = set(range(len(index.documents)))
        expr_ids = self.expr.search(index)
        return all_ids - expr_ids

    def __repr__(self):
        return f"NOT ({self.expr})"


class ANDNOT(Binary):
    def evaluate(self, doc):
        return self.left.evaluate(doc) and not self.right.evaluate(doc)

    def search(self, index):
        left_ids = self.left.search(index)
        right_ids = self.right.search(index)
        return left_ids - right_ids

    def __repr__(self):
        return f"({self.left}) AND NOT ({self.right})"
