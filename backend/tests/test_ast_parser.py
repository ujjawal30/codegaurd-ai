"""
Tests for app.services.tools.ast_parser
"""

import pytest
from app.services.tools.ast_parser import analyze_file, analyze_files
from tests.conftest import (
    SAMPLE_PYTHON_SIMPLE,
    SAMPLE_PYTHON_COMPLEX,
    SAMPLE_PYTHON_SYNTAX_ERROR,
    SAMPLE_PYTHON_WITH_MAIN,
)


# ── analyze_file ────────────────────────────────────────────────


class TestAnalyzeFile:
    """Tests for the analyze_file function."""

    def test_extracts_functions(self):
        result = analyze_file("test.py", SAMPLE_PYTHON_SIMPLE)
        func_names = [f.name for f in result.functions]
        assert "greet" in func_names
        assert "async_fetch" in func_names

    def test_detects_async_functions(self):
        result = analyze_file("test.py", SAMPLE_PYTHON_SIMPLE)
        async_fn = next(f for f in result.functions if f.name == "async_fetch")
        assert async_fn.is_async is True

    def test_extracts_function_args(self):
        result = analyze_file("test.py", SAMPLE_PYTHON_SIMPLE)
        greet = next(f for f in result.functions if f.name == "greet")
        assert "name" in greet.args

    def test_extracts_function_docstring(self):
        result = analyze_file("test.py", SAMPLE_PYTHON_SIMPLE)
        greet = next(f for f in result.functions if f.name == "greet")
        assert greet.docstring is not None
        assert "greeting" in greet.docstring.lower()

    def test_extracts_classes(self):
        result = analyze_file("test.py", SAMPLE_PYTHON_SIMPLE)
        class_names = [c.name for c in result.classes]
        assert "UserService" in class_names

    def test_extracts_class_methods(self):
        result = analyze_file("test.py", SAMPLE_PYTHON_SIMPLE)
        user_svc = next(c for c in result.classes if c.name == "UserService")
        method_names = [m.name for m in user_svc.methods]
        assert "__init__" in method_names
        assert "get_user" in method_names
        assert "validate_email" in method_names

    def test_extracts_class_docstring(self):
        result = analyze_file("test.py", SAMPLE_PYTHON_SIMPLE)
        user_svc = next(c for c in result.classes if c.name == "UserService")
        assert user_svc.docstring is not None

    def test_extracts_imports(self):
        result = analyze_file("test.py", SAMPLE_PYTHON_SIMPLE)
        import_modules = [i.module for i in result.imports]
        assert "os" in import_modules
        assert "typing" in import_modules

    def test_detects_from_import(self):
        result = analyze_file("test.py", SAMPLE_PYTHON_SIMPLE)
        typing_import = next(i for i in result.imports if i.module == "typing")
        assert typing_import.is_from_import is True
        assert "Optional" in typing_import.names

    def test_counts_total_lines(self):
        result = analyze_file("test.py", SAMPLE_PYTHON_SIMPLE)
        assert result.total_lines > 0

    def test_file_path_is_set(self):
        result = analyze_file("my_module.py", SAMPLE_PYTHON_SIMPLE)
        assert result.file_path == "my_module.py"

    def test_detects_static_method_decorator(self):
        result = analyze_file("test.py", SAMPLE_PYTHON_SIMPLE)
        user_svc = next(c for c in result.classes if c.name == "UserService")
        validate = next(m for m in user_svc.methods if m.name == "validate_email")
        assert "staticmethod" in validate.decorators


class TestComplexity:
    """Tests for cyclomatic complexity computation."""

    def test_simple_function_low_complexity(self):
        result = analyze_file("test.py", SAMPLE_PYTHON_SIMPLE)
        greet = next(f for f in result.functions if f.name == "greet")
        assert greet.complexity == 1  # No branches

    def test_complex_function_high_complexity(self):
        result = analyze_file("test.py", SAMPLE_PYTHON_COMPLEX)
        cfn = next(f for f in result.functions if f.name == "complex_function")
        assert cfn.complexity > 5  # Many branches

    def test_method_with_branch_has_complexity(self):
        result = analyze_file("test.py", SAMPLE_PYTHON_SIMPLE)
        user_svc = next(c for c in result.classes if c.name == "UserService")
        get_user = next(m for m in user_svc.methods if m.name == "get_user")
        assert get_user.complexity >= 2  # Has an if


class TestEdgeCases:
    """Edge case handling."""

    def test_syntax_error_returns_empty_result(self):
        result = analyze_file("bad.py", SAMPLE_PYTHON_SYNTAX_ERROR)
        assert result.functions == []
        assert result.classes == []

    def test_empty_file(self):
        result = analyze_file("empty.py", "")
        assert result.functions == []
        assert result.classes == []
        assert result.total_lines == 1  # empty string = 1 line

    def test_detects_main_guard(self):
        result = analyze_file("script.py", SAMPLE_PYTHON_WITH_MAIN)
        assert result.has_main_guard is True

    def test_no_main_guard(self):
        result = analyze_file("lib.py", SAMPLE_PYTHON_SIMPLE)
        assert result.has_main_guard is False


# ── analyze_files (batch) ───────────────────────────────────────


class TestAnalyzeFiles:
    """Tests for the batch analyze_files function."""

    @pytest.mark.asyncio
    async def test_analyzes_multiple_files(self):
        files = [
            {"path": "a.py", "content": SAMPLE_PYTHON_SIMPLE},
            {"path": "b.py", "content": SAMPLE_PYTHON_COMPLEX},
        ]
        results = await analyze_files(files)
        assert "a.py" in results
        assert "b.py" in results

    @pytest.mark.asyncio
    async def test_returns_dict_of_ast_analysis(self):
        files = [{"path": "x.py", "content": SAMPLE_PYTHON_SIMPLE}]
        results = await analyze_files(files)
        assert results["x.py"].file_path == "x.py"
        assert len(results["x.py"].functions) > 0
