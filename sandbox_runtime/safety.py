"""Safety utilities for code validation inside the sandbox."""

from __future__ import annotations

import ast
from typing import Any, Dict, Optional

_ALLOWED_NODES = {
    ast.Module,
    ast.Expr,
    ast.Call,
    ast.Assign,
    ast.AugAssign,
    ast.AnnAssign,
    ast.Attribute,
    ast.Subscript,
    ast.Name,
    ast.Load,
    ast.Store,
    ast.Constant,
    ast.List,
    ast.Tuple,
    ast.Dict,
    ast.Set,
    ast.ListComp,
    ast.DictComp,
    ast.SetComp,
    ast.GeneratorExp,
    ast.keyword,
    ast.If,
    ast.IfExp,
    ast.Compare,
    ast.BoolOp,
    ast.BinOp,
    ast.UnaryOp,
    ast.Not,
    ast.And,
    ast.Or,
    ast.In,
    ast.NotIn,
    ast.Is,
    ast.IsNot,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Pow,
    ast.FloorDiv,
    ast.USub,
    ast.UAdd,
    ast.For,
    ast.While,
    ast.Break,
    ast.Continue,
    ast.Pass,
    ast.Return,
    ast.Raise,
    ast.NamedExpr,
}

_DISALLOWED_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.Global,
    ast.Nonlocal,
    ast.Lambda,
    ast.ClassDef,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.Await,
    ast.Yield,
    ast.YieldFrom,
    ast.AsyncFor,
    ast.AsyncWith,
    ast.With,
    ast.Try,
)

_DISALLOWED_NAMES = {"__import__", "eval", "exec", "open", "compile"}

_ALLOWED_BUILTINS: Dict[str, Any] = {
    "len": len,
    "range": range,
    "enumerate": enumerate,
    "min": min,
    "max": max,
    "sum": sum,
    "sorted": sorted,
    "any": any,
    "all": all,
    "map": map,
    "filter": filter,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "abs": abs,
    "round": round,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "zip": zip,
    "isinstance": isinstance,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "Exception": Exception,
}


class SafetyError(RuntimeError):
    """Raised when generated code violates safety constraints."""


def _ensure_allowed(node: ast.AST) -> None:
    if isinstance(node, _DISALLOWED_NODES):
        raise SafetyError(f"Disallowed syntax: {type(node).__name__}")
    if type(node) not in _ALLOWED_NODES:
        raise SafetyError(f"Unsupported syntax: {type(node).__name__}")

    if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
        raise SafetyError("Access to dunder attributes is not permitted")

    if isinstance(node, ast.Name) and node.id in _DISALLOWED_NAMES:
        raise SafetyError(f"Usage of {node.id!r} is not permitted")

    if isinstance(node, ast.Call):
        callee = node.func
        if isinstance(callee, ast.Name) and callee.id in _DISALLOWED_NAMES:
            raise SafetyError(f"Call to {callee.id!r} is not permitted")

    for child in ast.iter_child_nodes(node):
        _ensure_allowed(child)


def validate_code(source: str) -> None:
    """Validate that the generated code complies with the sandbox policy."""

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:  # pragma: no cover - sanity check
        raise SafetyError(f"Generated code has syntax error: {exc}") from exc

    _ensure_allowed(tree)


def safe_exec(source: str, globals_dict: dict[str, Any], locals_dict: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Execute code using sandbox safe guards."""

    validate_code(source)

    sandbox_globals: Dict[str, Any] = {"__builtins__": _ALLOWED_BUILTINS}
    sandbox_globals.update(globals_dict)

    sandbox_locals: Dict[str, Any]
    if locals_dict is None:
        sandbox_locals = {}
    else:
        sandbox_locals = locals_dict

    compiled = compile(source, "<sandbox>", "exec")
    exec(compiled, sandbox_globals, sandbox_locals)

    return sandbox_locals if locals_dict is not None else sandbox_globals
