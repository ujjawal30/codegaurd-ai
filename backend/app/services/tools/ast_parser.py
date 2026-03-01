"""
CodeGuard AI — AST Parser Service.

Extracts structural information from Python files using the ast module:
function signatures, class hierarchies, imports, and complexity estimates.
"""

import ast
from typing import Optional

from app.core.logging import get_logger
from app.schemas.analysis import (
    ASTAnalysis,
    ClassInfo,
    FunctionInfo,
    ImportInfo,
)

logger = get_logger(__name__)


# ═════════════════════════════════════════════════════════════════
# Complexity Visitor — McCabe-style cyclomatic complexity
# ═════════════════════════════════════════════════════════════════

class ComplexityVisitor(ast.NodeVisitor):
    """Counts branching nodes to estimate McCabe cyclomatic complexity."""

    def __init__(self) -> None:
        self.complexity = 1  # Base complexity

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # Each `and`/`or` adds a branch
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.complexity += 1
        self.complexity += len(node.ifs)
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.complexity += 1
        self.generic_visit(node)


def _compute_complexity(node: ast.AST) -> int:
    """Compute McCabe cyclomatic complexity for a function/method AST node."""
    visitor = ComplexityVisitor()
    visitor.visit(node)
    return visitor.complexity


# ═════════════════════════════════════════════════════════════════
# AST Extraction Helpers
# ═════════════════════════════════════════════════════════════════

def _get_docstring(node: ast.AST) -> Optional[str]:
    """Extract docstring from a function or class node."""
    try:
        return ast.get_docstring(node)
    except TypeError:
        return None


def _get_decorators(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> list[str]:
    """Extract decorator names as strings."""
    decorators = []
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            decorators.append(dec.id)
        elif isinstance(dec, ast.Attribute):
            decorators.append(ast.unparse(dec))
        elif isinstance(dec, ast.Call):
            if isinstance(dec.func, ast.Name):
                decorators.append(dec.func.id)
            elif isinstance(dec.func, ast.Attribute):
                decorators.append(ast.unparse(dec.func))
            else:
                decorators.append(ast.unparse(dec))
        else:
            decorators.append(ast.unparse(dec))
    return decorators


def _extract_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionInfo:
    """Extract function information from an AST node."""
    args = []
    for arg in node.args.args:
        args.append(arg.arg)
    for arg in node.args.kwonlyargs:
        args.append(arg.arg)
    if node.args.vararg:
        args.append(f"*{node.args.vararg.arg}")
    if node.args.kwarg:
        args.append(f"**{node.args.kwarg.arg}")

    return FunctionInfo(
        name=node.name,
        lineno=node.lineno,
        end_lineno=node.end_lineno,
        args=args,
        decorators=_get_decorators(node),
        docstring=_get_docstring(node),
        is_async=isinstance(node, ast.AsyncFunctionDef),
        complexity=_compute_complexity(node),
    )


def _extract_class(node: ast.ClassDef) -> ClassInfo:
    """Extract class information from an AST node."""
    bases = [ast.unparse(base) for base in node.bases]
    methods = []

    for item in ast.walk(node):
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item is not node:
            # Only include direct methods, not nested functions
            for child in ast.iter_child_nodes(node):
                if child is item:
                    methods.append(_extract_function(item))
                    break

    return ClassInfo(
        name=node.name,
        lineno=node.lineno,
        end_lineno=node.end_lineno,
        bases=bases,
        methods=methods,
        docstring=_get_docstring(node),
    )


def _extract_imports(tree: ast.Module) -> list[ImportInfo]:
    """Extract all import statements from the AST."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(ImportInfo(
                    module=alias.name,
                    names=[alias.asname or alias.name],
                    is_from_import=False,
                    lineno=node.lineno,
                ))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [alias.name for alias in node.names]
            imports.append(ImportInfo(
                module=module,
                names=names,
                is_from_import=True,
                lineno=node.lineno,
            ))
    return imports


def _has_main_guard(tree: ast.Module) -> bool:
    """Check if the file has an `if __name__ == '__main__':` guard."""
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            try:
                test_str = ast.unparse(node.test)
                if "__name__" in test_str and "__main__" in test_str:
                    return True
            except Exception:
                continue
    return False


# ═════════════════════════════════════════════════════════════════
# Public API
# ═════════════════════════════════════════════════════════════════

def analyze_file(file_path: str, content: str) -> ASTAnalysis:
    """
    Parse a Python file and extract structural information.

    Args:
        file_path: Relative path of the file.
        content: Full source code content.

    Returns:
        ASTAnalysis with functions, classes, imports, and complexity data.
    """
    try:
        tree = ast.parse(content, filename=file_path)
    except SyntaxError as e:
        logger.warning("ast_parse_failed", file=file_path, error=str(e))
        return ASTAnalysis(
            file_path=file_path,
            total_lines=content.count("\n") + 1,
        )

    # Extract top-level functions
    functions = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(_extract_function(node))

    # Extract top-level classes
    classes = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(_extract_class(node))

    return ASTAnalysis(
        file_path=file_path,
        functions=functions,
        classes=classes,
        imports=_extract_imports(tree),
        total_lines=content.count("\n") + 1,
        has_main_guard=_has_main_guard(tree),
    )


async def analyze_files(files: list[dict]) -> dict[str, ASTAnalysis]:
    """
    Analyze multiple Python files.

    Args:
        files: List of dicts with 'path' and 'content' keys.

    Returns:
        Dict mapping file path to ASTAnalysis result.
    """
    results = {}
    for f in files:
        path = f["path"]
        content = f["content"]
        try:
            results[path] = analyze_file(path, content)
        except Exception as e:
            logger.error("ast_analysis_failed", file=path, error=str(e))
            results[path] = ASTAnalysis(
                file_path=path,
                total_lines=content.count("\n") + 1,
            )
    return results
