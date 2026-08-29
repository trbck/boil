#!/usr/bin/env python3
"""boil-assert-db — the data sensor.

A milestone `check` is any command whose exit code is the verdict. This turns a
query plus an assertion into such a command, so a goal can be measured from the
project's own data, not only from its tests:

    boil-assert-db.py --db runs/data/registry.duckdb \
        --query "select sharpe from runs where strategy='x' order by created_at desc limit 1" \
        --assert "sharpe >= 0.8"

The first row's columns are bound as names; the assertion is interpreted over an
AST whitelist (bool / compare / arithmetic / ifexp / tuple over names and
constants; calls only to abs/min/max/len/round). Never eval(): attribute chains
like `().__class__` are rejected, so a check cannot be talked into passing.

Exit codes (the verdict):  0 PASS   1 FAIL (incl. "no rows")   2 ERROR (missing db,
query error, bad expression) — an ERROR is a broken sensor, never a pass.

Ported from helm's `helmlib/sensors.py` (2026-08-29). Stdlib only; duckdb is
imported lazily and only when the engine is duckdb.
"""
from __future__ import annotations

import argparse
import ast
import operator
import sys
from pathlib import Path

SAFE_BUILTINS = {"abs": abs, "min": min, "max": max, "len": len, "round": round}
CMP_OPS = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne,
    ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.Gt: operator.gt, ast.GtE: operator.ge,
    ast.Is: operator.is_, ast.IsNot: operator.is_not,
    ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
}
BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv, ast.Pow: operator.pow,
}
UNARY_OPS = {ast.Not: operator.not_, ast.USub: operator.neg, ast.UAdd: operator.pos}
SQLITE_SUFFIXES = {".sqlite", ".sqlite3"}


def eval_assertion(expression: str, env: dict):
    """Interpret `expression` over `env` through the AST whitelist. Raises on anything else."""
    tree = ast.parse(expression, mode="eval")

    def ev(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            raise NameError(f"unknown name {node.id!r} — not a column of the query row")
        if isinstance(node, ast.BoolOp):
            short = isinstance(node.op, ast.Or)
            result = not short
            for v in node.values:
                result = ev(v)
                if bool(result) == short:
                    return result
            return result
        if isinstance(node, ast.UnaryOp):
            op = UNARY_OPS.get(type(node.op))
            if op is None:
                raise ValueError(f"disallowed unary operator {type(node.op).__name__}")
            return op(ev(node.operand))
        if isinstance(node, ast.BinOp):
            op = BIN_OPS.get(type(node.op))
            if op is None:
                raise ValueError(f"disallowed binary operator {type(node.op).__name__}")
            return op(ev(node.left), ev(node.right))
        if isinstance(node, ast.Compare):
            left = ev(node.left)
            for op_node, comparator in zip(node.ops, node.comparators):
                op = CMP_OPS.get(type(op_node))
                if op is None:
                    raise ValueError(f"disallowed comparison {type(op_node).__name__}")
                right = ev(comparator)
                if not op(left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_BUILTINS:
                raise ValueError("only calls to abs/min/max/len/round are allowed")
            if node.keywords:
                raise ValueError("keyword arguments are not allowed in assert calls")
            return SAFE_BUILTINS[node.func.id](*[ev(a) for a in node.args])
        if isinstance(node, ast.IfExp):
            return ev(node.body) if ev(node.test) else ev(node.orelse)
        if isinstance(node, ast.Tuple):
            return tuple(ev(e) for e in node.elts)
        raise ValueError(f"disallowed expression element {type(node).__name__}")

    return ev(tree.body)


def fetch_first_row(db: Path, query: str, engine: str) -> tuple[list[str], tuple | None]:
    """(column names, first row or None). Read-only in both engines."""
    if engine == "sqlite":
        import sqlite3
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            cur = con.execute(query)
            cols = [d[0] for d in cur.description]
            return cols, cur.fetchone()
        finally:
            con.close()
    try:
        import duckdb  # optional dependency
    except ImportError as e:  # pragma: no cover - environment dependent
        raise RuntimeError("duckdb is not installed (pip install duckdb, or use --engine sqlite)") from e
    con = duckdb.connect(str(db), read_only=True)
    try:
        cur = con.execute(query)
        cols = [d[0] for d in cur.description]
        return cols, cur.fetchone()
    finally:
        con.close()


def fmt(v) -> str:
    return f"{v:.4g}" if isinstance(v, float) else str(v)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True, help="database file (duckdb or sqlite)")
    ap.add_argument("--query", required=True, help="SQL; the FIRST row's columns become assert names")
    ap.add_argument("--assert", dest="expr", required=True, help="expression over the row, e.g. 'sharpe >= 0.8'")
    ap.add_argument("--engine", choices=("duckdb", "sqlite"), default=None,
                    help="default: sqlite for .sqlite/.sqlite3, otherwise duckdb")
    a = ap.parse_args(argv)

    db = Path(a.db)
    engine = a.engine or ("sqlite" if db.suffix in SQLITE_SUFFIXES else "duckdb")
    if not db.is_file():
        print(f"ERROR missing db {db} | assert {a.expr}")
        return 2
    try:
        cols, row = fetch_first_row(db, a.query, engine)
    except Exception as e:  # noqa: BLE001 — any query problem is a broken sensor
        print(f"ERROR query failed: {str(e).splitlines()[0][:200]} | assert {a.expr}")
        return 2
    if row is None:
        print(f"FAIL no rows | assert {a.expr}")
        return 1
    env = dict(zip(cols, row))
    try:
        ok = bool(eval_assertion(a.expr, env))
    except Exception as e:  # noqa: BLE001
        print(f"ERROR assert failed to eval: {e} | assert {a.expr}")
        return 2
    actual = ", ".join(f"{k}={fmt(v)}" for k, v in env.items())
    print(f"{'PASS' if ok else 'FAIL'} {actual} | assert {a.expr}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
