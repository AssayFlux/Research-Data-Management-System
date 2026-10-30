"""Safe expression evaluator (AST-based, no eval)."""
import ast, operator, math

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
       ast.USub: operator.neg, ast.UAdd: operator.pos}

FUNCS = {
    "abs": abs, "sqrt": math.sqrt, "pow": pow,
    "log": math.log, "ln": math.log, "log10": math.log10, "log2": math.log2,
    "exp": math.exp, "round": round,
    "min": min, "max": max,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
}

CONSTS = {"pi": math.pi, "e": math.e}


class _E(ast.NodeVisitor):
    def __init__(self, names):
        self.n = dict(CONSTS)
        self.n.update(names or {})

    def visit_Expression(self, node): return self.visit(node.body)

    def visit_Constant(self, node):
        if isinstance(node.value, (int, float)): return node.value
        raise ValueError("Bad constant")

    def visit_Name(self, node):
        if node.id in self.n: return self.n[node.id]
        raise ValueError(f"Unknown variable: {node.id}")

    def visit_BinOp(self, node):
        op = OPS.get(type(node.op))
        if not op: raise ValueError("Operator not allowed")
        return op(self.visit(node.left), self.visit(node.right))

    def visit_UnaryOp(self, node):
        op = OPS.get(type(node.op))
        if not op: raise ValueError("Operator not allowed")
        return op(self.visit(node.operand))

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name) or node.func.id not in FUNCS:
            raise ValueError("Function not allowed")
        return FUNCS[node.func.id](*[self.visit(a) for a in node.args])

    def generic_visit(self, node):
        raise ValueError("Unsupported expression")


def calculate(expr, values):
    return _E(values).visit(ast.parse(expr, mode="eval"))


def test_formula(expr, sample=None):
    try:
        import re
        names = sorted(set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", expr))
                       - set(FUNCS) - set(CONSTS))
        vals = {n: (sample or {}).get(n, 1.0) for n in names}
        return True, calculate(expr, vals), names
    except Exception as e:
        return False, str(e), []


def substitute_codes(expression, mapping):
    """Replace input placeholder names with real parameter codes.
    mapping: {'weight': 'WT', 'height': 'HT'}"""
    import re
    # longest first to avoid partial collisions
    keys = sorted(mapping.keys(), key=len, reverse=True)
    out = expression
    for k in keys:
        out = re.sub(rf"\b{re.escape(k)}\b", mapping[k], out)
    return out
