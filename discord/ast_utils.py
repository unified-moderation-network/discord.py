"""
The MIT License (MIT)

Copyright (c) 2021-present Michael Hall

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

import inspect
import ast 
import sys
from typing import Callable, TypeVar

T = TypeVar("T")

_cycle_blocked = False

def nodebuglog(logname: str = "logging") -> Callable[[T], T]:
    """Decorator which rewrites ast

    The ast rewriting only happens with python -O ...

    This should only be used with knowledge that:

    1. removing all nodes which begin with "logging" is safe.
    2. logging is actually a measurable issue in production.
    3. That it will not result in an empty function body.
    4. Understanding that this causes divergence in production/test environment behavior.
    5. At your own risk.
    """

    class _Transformer(ast.NodeTransformer):
           
        def visit_Expr(self, node):
            try:
                if node.value.func.value.id == logname and node.value.func.attr == "debug":
                    return None
            except (ValueError, AttributeError):
                pass
            return node
    
    _transformer = _Transformer()
    
    def ast_rewriter(f: T) -> T:

        # This is only because of the performance impact of logging in tight loops in production.
        # debug logging is still useful in other places and
        # even in the tight loops when diagnosing specific issues.
        if __debug__:
            return f

        # Prevents a cyclic compile issue
        global _cycle_blocked
        if _cycle_blocked:
            return f

        original_ast = ast.parse(inspect.getsource(f))

        new_ast = compile(_transformer.visit(original_ast),'<string>','exec')

        env = sys.modules[f.__module__].__dict__
        
        _cycle_blocked = True
        try:
            exec(new_ast, env)
        finally:
            _cycle_blocked = False
        return env[f.__name__]

    return ast_rewriter