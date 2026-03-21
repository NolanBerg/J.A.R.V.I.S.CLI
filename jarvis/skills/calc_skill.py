"""Calculator skill for Jarvis CLI.

Commands:
  calc <expression>   Evaluate a math expression safely
"""
from __future__ import annotations

import ast
import math
import operator

from jarvis.core import jarvis_say, register

# Allowed operators for safe evaluation
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.BitAnd: operator.and_,
    ast.BitOr: operator.or_,
    ast.BitXor: operator.xor,
    ast.LShift: operator.lshift,
    ast.RShift: operator.rshift,
    ast.Invert: operator.invert,
}

# Safe math constants
_NAMES = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
}

# Safe math functions
_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "ceil": math.ceil,
    "floor": math.floor,
    "factorial": math.factorial,
    "gcd": math.gcd,
    "pow": math.pow,
    "hex": hex,
    "bin": bin,
    "oct": oct,
}


def _safe_eval(node: ast.AST):
    """Recursively evaluate an AST node with only safe operations."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, complex)):
            return node.value
        raise ValueError(f"Unsupported constant: {node.value!r}")

    if isinstance(node, ast.UnaryOp):
        op_fn = _OPERATORS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op_fn(_safe_eval(node.operand))

    if isinstance(node, ast.BinOp):
        op_fn = _OPERATORS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        # Guard against absurd exponents
        if isinstance(node.op, ast.Pow) and isinstance(right, (int, float)) and right > 10000:
            raise ValueError("Exponent too large (max 10000).")
        return op_fn(left, right)

    if isinstance(node, ast.Name):
        if node.id in _NAMES:
            return _NAMES[node.id]
        raise ValueError(f"Unknown name: '{node.id}'")

    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS:
            args = [_safe_eval(arg) for arg in node.args]
            return _FUNCTIONS[node.func.id](*args)
        raise ValueError(f"Unknown function: '{ast.dump(node.func)}'")

    raise ValueError(f"Unsupported expression: {type(node).__name__}")


@register("calc", aliases=["math"], description="Evaluate a math expression. Usage: calc 2**16 + 1")
def handle_calc(raw: str) -> None:
    parts = raw.strip().split(None, 1)
    expr = parts[1].strip() if len(parts) > 1 else ""

    if not expr:
        jarvis_say("Usage: calc <expression>  (e.g. calc 2**16 + 1)")
        return

    try:
        tree = ast.parse(expr, mode="eval")
        result = _safe_eval(tree)
    except (ValueError, TypeError, SyntaxError, ZeroDivisionError, OverflowError) as e:
        jarvis_say(f"[red]Error:[/red] {e}")
        return

    # Format result nicely
    if isinstance(result, float) and result == int(result) and not math.isinf(result):
        display = str(int(result))
    else:
        display = str(result)

    jarvis_say(f"[bold green]{display}[/bold green]")
