"""Utilidad para cargar módulos desde .pyc cuando falta el fuente."""

from __future__ import annotations

import marshal
import sys
import types
from pathlib import Path


def bootstrap_pyc(module_name: str, py_file: str | Path) -> types.ModuleType:
    py_path = Path(py_file)
    module = sys.modules[module_name]
    if getattr(module, "__bootstrapped__", False):
        return module
    if getattr(module, "__bootstrapping__", False):
        return module

    pyc = py_path.parent / "__pycache__" / f"{py_path.stem}.cpython-314.pyc"
    if not pyc.exists() or pyc.stat().st_size < 1024:
        raise ImportError(
            f"Bytecode ausente o invalido para {module_name}. "
            f"Se necesita reimplementar {py_path.name}."
        )

    module.__bootstrapping__ = True
    try:
        code = marshal.loads(pyc.read_bytes()[16:])
        module.__file__ = str(py_path)
        exec(code, module.__dict__)
        module.__bootstrapped__ = True
    finally:
        module.__bootstrapping__ = False
    return module
