"""
ast_parser.py — Source code entity extraction using Python's built-in AST.

What this module does:
  For each source file in a commit, parse the code and extract:
    - Function / method names and their line numbers
    - Class names
    - Import statements (which modules this file depends on)
    - Call relationships (which functions call which)

  These extracted entities become the nodes and edges of the Knowledge Graph
  built by `graph_builder.py`.

Languages supported:
  - Python (.py) : Full AST via Python's built-in `ast` module
  - JavaScript / TypeScript (.js, .ts, .jsx, .tsx) :
      Regex-based extraction (no external parser). Less precise but fast and
      dependency-free. Extracts function/class names and import statements.

Libraries:
  - ast     : Python's built-in Abstract Syntax Tree parser. Zero dependencies.
              Works by parsing Python source text into a tree of AST nodes.
  - re      : Regular expressions for JS/TS extraction.

Design notes:
  We only parse files that were *changed* in a given commit (not the whole repo).
  This is the "No Index" approach described in the architecture: parse on demand,
  discard after computing the graph delta.
"""

import ast
import re
import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes representing extracted code entities
# ---------------------------------------------------------------------------

@dataclass
class FunctionInfo:
    """A function or method found in source code."""
    name: str
    file_path: str
    line_number: int
    complexity: float = 1.0     # Overwritten by metrics_engine.py


@dataclass
class ClassInfo:
    """A class definition found in source code."""
    name: str
    file_path: str
    line_number: int
    bases: List[str] = field(default_factory=list)   # parent class names


@dataclass
class ImportInfo:
    """An import statement found in source code."""
    source_file: str      # file that contains the import
    imported_module: str  # what is being imported (module name or path)
    imported_names: List[str] = field(default_factory=list)


@dataclass
class CallInfo:
    """A function call found inside a function body."""
    caller_function: str   # name of the function that makes the call
    caller_file: str
    callee_name: str       # name of the function being called


@dataclass
class FileEntities:
    """All extracted entities from a single source file."""
    file_path: str
    language: str               # "python" | "javascript" | "typescript" | "unknown"
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    imports: List[ImportInfo] = field(default_factory=list)
    calls: List[CallInfo] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Python AST parser
# ---------------------------------------------------------------------------

class _PythonCallVisitor(ast.NodeVisitor):
    """
    AST visitor that collects function calls made inside a function body.
    Used to build call-graph edges for Python functions.
    """
    def __init__(self, caller_name: str, file_path: str):
        self.caller_name = caller_name
        self.file_path = file_path
        self.calls: List[CallInfo] = []

    def visit_Call(self, node: ast.Call):
        callee = None
        if isinstance(node.func, ast.Name):
            callee = node.func.id
        elif isinstance(node.func, ast.Attribute):
            callee = node.func.attr
        if callee:
            self.calls.append(CallInfo(
                caller_function=self.caller_name,
                caller_file=self.file_path,
                callee_name=callee,
            ))
        self.generic_visit(node)


def _parse_python(source: str, file_path: str) -> FileEntities:
    """
    Parse Python source code using the built-in `ast` module.

    Extracts:
      - All function and method definitions
      - All class definitions (with base classes)
      - All import statements (`import x`, `from x import y`)
      - All function calls within each function body

    Args:
        source    : Raw Python source code text
        file_path : Relative path of the file in the repo

    Returns:
        FileEntities populated with functions, classes, imports, calls
    """
    entities = FileEntities(file_path=file_path, language="python")

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as e:
        logger.debug(f"Python syntax error in {file_path}: {e}")
        return entities

    for node in ast.walk(tree):
        # --- Functions & Methods ---
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn = FunctionInfo(
                name=node.name,
                file_path=file_path,
                line_number=node.lineno,
            )
            entities.functions.append(fn)

            # Extract calls within this function
            visitor = _PythonCallVisitor(node.name, file_path)
            visitor.visit(node)
            entities.calls.extend(visitor.calls)

        # --- Classes ---
        elif isinstance(node, ast.ClassDef):
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)
            entities.classes.append(ClassInfo(
                name=node.name,
                file_path=file_path,
                line_number=node.lineno,
                bases=bases,
            ))

        # --- Imports (import x) ---
        elif isinstance(node, ast.Import):
            for alias in node.names:
                entities.imports.append(ImportInfo(
                    source_file=file_path,
                    imported_module=alias.name,
                ))

        # --- Imports (from x import y) ---
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [a.name for a in node.names]
            entities.imports.append(ImportInfo(
                source_file=file_path,
                imported_module=module,
                imported_names=names,
            ))

    return entities


# ---------------------------------------------------------------------------
# JavaScript / TypeScript regex parser
# ---------------------------------------------------------------------------

# Patterns for JS/TS extraction
_JS_FUNCTION_RE = re.compile(
    r"""
    (?:                         # function keyword forms
        (?:export\s+)?(?:default\s+)?(?:async\s+)?
        function\s+(\w+)\s*\(    # function name
    ) |
    (?:                         # arrow / const forms
        (?:export\s+)?(?:const|let|var)\s+(\w+)\s*=
        \s*(?:async\s+)?\(.*?\)\s*=>
    ) |
    (?:                         # class method
        ^\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{
    )
    """,
    re.VERBOSE | re.MULTILINE,
)

_JS_CLASS_RE = re.compile(
    r"""
    (?:export\s+)?(?:default\s+)?
    class\s+(\w+)               # class name
    (?:\s+extends\s+(\w+))?     # optional base class
    """,
    re.VERBOSE,
)

_JS_IMPORT_RE = re.compile(
    r"""
    import\s+
    (?:
        (?:\{[^}]+\}|[\w*]+)    # named or namespace imports
        \s+from\s+
    )?
    ['"]([^'"]+)['"]            # module path
    """,
    re.VERBOSE,
)


def _parse_javascript(source: str, file_path: str) -> FileEntities:
    """
    Regex-based extraction for JavaScript and TypeScript files.

    Less precise than a full AST parser but has zero external dependencies
    and handles JSX/TSX syntax that would confuse simpler parsers.

    Extracts functions, classes, and import statements.
    Call relationships are NOT extracted for JS/TS (would require a proper parser).
    """
    entities = FileEntities(file_path=file_path, language="javascript")

    lines = source.splitlines()

    # Functions
    for match in _JS_FUNCTION_RE.finditer(source):
        name = match.group(1) or match.group(2) or match.group(3)
        if name and not name.startswith("_"):  # skip private-ish names
            line_no = source[:match.start()].count("\n") + 1
            entities.functions.append(FunctionInfo(
                name=name,
                file_path=file_path,
                line_number=line_no,
            ))

    # Classes
    for match in _JS_CLASS_RE.finditer(source):
        name = match.group(1)
        base = match.group(2)
        line_no = source[:match.start()].count("\n") + 1
        entities.classes.append(ClassInfo(
            name=name,
            file_path=file_path,
            line_number=line_no,
            bases=[base] if base else [],
        ))

    # Imports
    for match in _JS_IMPORT_RE.finditer(source):
        module_path = match.group(1)
        entities.imports.append(ImportInfo(
            source_file=file_path,
            imported_module=module_path,
        ))

    return entities


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_file(source: str, file_path: str) -> Optional[FileEntities]:
    """
    Dispatch to the correct parser based on file extension.

    Args:
        source    : Raw file content as text
        file_path : File path (used for extension detection and labelling)

    Returns:
        FileEntities or None if the file type is not supported
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".py":
        return _parse_python(source, file_path)
    elif ext in {".js", ".jsx", ".ts", ".tsx"}:
        return _parse_javascript(source, file_path)
    else:
        return None


def parse_changed_files(file_contents: dict) -> List[FileEntities]:
    """
    Parse all changed files in a commit.

    Args:
        file_contents : dict mapping file_path → raw source text
                        (produced by git_ingestion.CommitInfo.file_contents)

    Returns:
        List of FileEntities, one per parseable file
    """
    results = []
    for file_path, source in file_contents.items():
        entity = parse_file(source, file_path)
        if entity is not None:
            results.append(entity)
    return results
