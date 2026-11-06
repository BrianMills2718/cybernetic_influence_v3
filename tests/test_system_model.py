"""The declared system model (docs/model/cybernetic_influence_model.toml) matches the code.

No model calls, no network. The code is read with Python's parser (``ast``) and
compared with the model in both directions, so a new, renamed or removed record
writer, API route, schema class or vocabulary value fails here until
docs/model/ is updated.

What is extracted, and from where:

- Store writes (logical writers): calls ``<receiver>.<method>(...)`` anywhere in
  src/ where ``method`` is a declared write method of a declared store class and
  the receiver is bound to that class in the same file, by ``name = Store(...)``,
  by a parameter annotation ``name: Store``, or by ``self.attr = name`` with
  ``name`` annotated as the store. A receiver bound to two store classes in one
  file fails the test rather than being guessed.
- Physical writes: every ``open(..., "w"/"x"/"a")``, ``Path.write_text``,
  ``Path.write_bytes``, ``unlink``, ``os.replace``/``os.rename``,
  one-argument ``Path.replace``/``Path.rename``, ``json.dump`` and ``shutil``
  move/copy/remove call in src/. Each must belong to a declared record.
- API routes: ``@app.<method>("/path")`` decorators in api.py and
  ``@simulator.<method>("/path")`` in public_waltzman.py, plus ``app.mount``.
- Kinds of things: every declared entity's defining class exists in its file;
  every field of ``GeneralSimulationProposalV1`` and ``ScenarioSpecV2`` maps to
  a declared entity, and every class in authoring_models.py is either an
  entity's defining class or a listed supporting class.
- Vocabularies: the ``Literal[...]`` values of declared fields.

Line numbers in the model are documentation; the test enforces file and
function, so a drifted line is a documentation fix, not a failure.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
MODEL_PATH = ROOT / "docs" / "model" / "cybernetic_influence_model.toml"
COVERAGE_PATH = ROOT / "docs" / "model" / "VIEW_COVERAGE.md"
PACKAGE = SRC / "cybernetic_influence"
AUTHORING_MODELS = PACKAGE / "general_simulation" / "authoring_models.py"
CONTRACTS_V2 = PACKAGE / "general_simulation" / "contracts_v2.py"
ROUTE_FILES = {
    PACKAGE / "api.py": "app",
    PACKAGE / "public_waltzman.py": "simulator",
}
HTTP_METHODS = {"get", "post", "put", "delete", "patch"}
COVERAGE_VALUES = {"shown", "partial", "hidden", "missing", "n/a"}
SHUTIL_WRITES = {"move", "copy", "copy2", "copyfile", "copytree", "rmtree"}

Site = tuple[str, str]  # (file relative to repo root, innermost function)


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def _function_at(tree: ast.Module, line: int) -> str:
    """Innermost function containing ``line``; ``<module>`` when none does."""
    best: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = node.end_lineno or node.lineno
            if node.lineno <= line <= end:
                if best is None or (end - node.lineno) < (
                    (best.end_lineno or best.lineno) - best.lineno
                ):
                    best = node
    return best.name if best is not None else "<module>"


def _str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _source_files() -> list[Path]:
    return [p for p in sorted(SRC.rglob("*.py")) if "__pycache__" not in p.parts]


def _annotation_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _store_bindings(tree: ast.Module, store_classes: set[str]) -> dict[str, set[str]]:
    """Receiver text (``runs``, ``self.store``) -> store classes it is bound to."""
    bindings: dict[str, set[str]] = {}

    def bind(name: str, cls: str) -> None:
        bindings.setdefault(name, set()).add(cls)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            annotated: dict[str, str] = {}
            arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            for arg in arguments:
                cls = _annotation_name(arg.annotation)
                if cls in store_classes:
                    assert cls is not None
                    annotated[arg.arg] = cls
                    bind(arg.arg, cls)
            for inner in ast.walk(node):
                if (
                    isinstance(inner, ast.Assign)
                    and len(inner.targets) == 1
                    and isinstance(inner.targets[0], ast.Attribute)
                    and isinstance(inner.targets[0].value, ast.Name)
                    and inner.targets[0].value.id == "self"
                    and isinstance(inner.value, ast.Name)
                    and inner.value.id in annotated
                ):
                    bind(f"self.{inner.targets[0].attr}", annotated[inner.value.id])
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id in store_classes
        ):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bind(target.id, node.value.func.id)
                elif (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    bind(f"self.{target.attr}", node.value.func.id)
    return bindings


def _receiver(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
        return f"self.{node.attr}"
    return None


def store_writes(stores: list[dict[str, Any]]) -> tuple[dict[str, set[Site]], list[str]]:
    """Store class -> sites that call one of its write methods; plus ambiguities."""
    methods = {store["class"]: set(store["write_methods"]) for store in stores}
    found: dict[str, set[Site]] = {cls: set() for cls in methods}
    ambiguous: list[str] = []
    for path in _source_files():
        tree = _parse(path)
        bindings = _store_bindings(tree, set(methods))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            receiver = _receiver(node.func.value)
            if receiver is None or receiver not in bindings:
                continue
            classes = {cls for cls in bindings[receiver] if node.func.attr in methods[cls]}
            if len(classes) > 1:
                ambiguous.append(f"{_rel(path)}:{node.lineno} {receiver}.{node.func.attr}")
            for cls in classes:
                found[cls].add((_rel(path), _function_at(tree, node.lineno)))
    return found, ambiguous


def _write_mode(node: ast.Call, positional_index: int) -> bool:
    mode: ast.AST | None = (
        node.args[positional_index] if len(node.args) > positional_index else None
    )
    for keyword in node.keywords:
        if keyword.arg == "mode":
            mode = keyword.value
    value = _str(mode)
    return value is not None and bool(set(value) & set("wxa"))


def physical_writes() -> set[Site]:
    """Every call in src/ that creates, replaces or removes a file."""
    found: set[Site] = set()
    for path in _source_files():
        tree = _parse(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            hit = False
            if isinstance(func, ast.Name) and func.id == "open":
                hit = _write_mode(node, 1)
            elif isinstance(func, ast.Attribute):
                owner = func.value.id if isinstance(func.value, ast.Name) else None
                if func.attr in {"write_text", "write_bytes", "unlink"}:
                    hit = True
                elif func.attr == "open":
                    hit = _write_mode(node, 0)
                elif func.attr in {"replace", "rename"} and owner == "os":
                    hit = True
                elif func.attr in {"replace", "rename"} and len(node.args) == 1 and not node.keywords:
                    hit = True  # Path.replace(target); str.replace takes two arguments
                elif func.attr == "dump" and owner == "json":
                    hit = True
                elif func.attr in SHUTIL_WRITES and owner == "shutil":
                    hit = True
            if hit:
                found.add((_rel(path), _function_at(tree, node.lineno)))
    return found


def api_routes() -> set[str]:
    routes: set[str] = set()
    for path, app_name in ROUTE_FILES.items():
        tree = _parse(path)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if (
                        isinstance(decorator, ast.Call)
                        and isinstance(decorator.func, ast.Attribute)
                        and isinstance(decorator.func.value, ast.Name)
                        and decorator.func.value.id == app_name
                        and decorator.func.attr in HTTP_METHODS
                    ):
                        route = _str(decorator.args[0]) if decorator.args else None
                        assert route is not None, f"{_rel(path)}:{decorator.lineno} non-literal route"
                        routes.add(f"{decorator.func.attr.upper()} {route}")
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "mount"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == app_name
            ):
                mounted = _str(node.args[0]) if node.args else None
                assert mounted is not None
                routes.add(f"MOUNT {mounted}")
    return routes


def classes_in(path: Path) -> dict[str, ast.ClassDef]:
    return {node.name: node for node in _parse(path).body if isinstance(node, ast.ClassDef)}


def _all_classes(path: Path) -> set[str]:
    return {node.name for node in ast.walk(_parse(path)) if isinstance(node, ast.ClassDef)}


def class_fields(path: Path, class_name: str) -> dict[str, ast.AST]:
    cls = classes_in(path)[class_name]
    return {
        item.target.id: item.annotation
        for item in cls.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }


def literal_values(annotation: ast.AST) -> set[str | int]:
    """All values inside every ``Literal[...]`` in an annotation."""
    values: set[str | int] = set()
    for node in ast.walk(annotation):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "Literal"
        ):
            items = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            for item in items:
                if isinstance(item, ast.Constant) and isinstance(item.value, (str, int)):
                    values.add(item.value)
    return values


def load_model() -> dict[str, Any]:
    with MODEL_PATH.open("rb") as handle:
        return tomllib.load(handle)


@pytest.fixture(scope="module")
def model() -> dict[str, Any]:
    loaded = load_model()
    assert loaded.get("schema") == "cybernetic-influence-system-model/v1"
    return loaded


def _sites(rows: list[dict[str, Any]]) -> set[Site]:
    return {(row["file"], row["function"]) for row in rows}


def test_every_store_write_is_declared_with_its_writer(model: dict[str, Any]) -> None:
    stores = model["stores"]
    found, ambiguous = store_writes(stores)
    assert ambiguous == [], f"store receivers bound to more than one store class: {ambiguous}"
    by_store = {record["store"]: record for record in model["records"] if record.get("store")}
    assert set(by_store) == {store["class"] for store in stores}, "every store has exactly one record"
    for cls, sites in found.items():
        record = by_store[cls]
        declared = _sites(record["writers"])
        assert sorted(sites - declared) == [], (
            f"record {record['name']!r}: {cls} is written in code at sites the model does not declare"
        )
        assert sorted(declared - sites) == [], (
            f"record {record['name']!r}: declared writers no longer write {cls} in code"
        )


def test_every_physical_write_belongs_to_a_declared_record(model: dict[str, Any]) -> None:
    declared: set[Site] = set()
    for record in model["records"]:
        declared |= _sites(record["physical_writers"])
    in_code = physical_writes()
    assert sorted(in_code - declared) == [], "files written in code by no declared record"
    assert sorted(declared - in_code) == [], "declared physical writers that no longer write files"


def test_store_classes_and_write_methods_exist(model: dict[str, Any]) -> None:
    for store in model["stores"]:
        path = ROOT / store["file"]
        cls = classes_in(path).get(store["class"])
        assert cls is not None, f"store class {store['class']} missing from {store['file']}"
        defined = {item.name for item in cls.body if isinstance(item, ast.FunctionDef)}
        missing = sorted(set(store["write_methods"]) - defined)
        assert missing == [], f"{store['class']} lacks declared write methods {missing}"


def test_api_routes_match(model: dict[str, Any]) -> None:
    declared = {route for process in model["processes"] for route in process.get("routes", [])}
    in_code = api_routes()
    assert sorted(in_code - declared) == [], "API routes in code but in no model process"
    assert sorted(declared - in_code) == [], "API routes in the model but not in code"


def test_entity_classes_exist(model: dict[str, Any]) -> None:
    for entity in model["entities"]:
        file_name, _, class_name = entity["class"].partition(":")
        if class_name:
            assert class_name in _all_classes(ROOT / file_name), (
                f"entity {entity['name']!r}: class {class_name} not found in {file_name}"
            )


def test_authoring_schema_kinds_are_all_declared(model: dict[str, Any]) -> None:
    entities = model["entities"]
    schema = model["authoring_schema"]
    for envelope_key, path in (("proposal_v1", AUTHORING_MODELS), ("scenario_v2", CONTRACTS_V2)):
        envelope = schema[envelope_key]
        fields = set(class_fields(path, envelope["class"]))
        mapped = {
            field
            for entity in entities
            for field in entity.get(f"{envelope_key}_fields", [])
        } | set(envelope["scalar_fields"])
        assert sorted(fields - mapped) == [], (
            f"{envelope['class']} fields with no declared entity (a new kind of thing?)"
        )
        assert sorted(mapped - fields) == [], f"model maps fields {envelope['class']} no longer has"
    declared_classes = {
        entity["class"].partition(":")[2]
        for entity in entities
        if entity["class"].startswith(_rel(AUTHORING_MODELS))
    } | set(schema["supporting_classes"])
    in_code = {name for name in classes_in(AUTHORING_MODELS) if not name.startswith("_")}
    assert sorted(in_code - declared_classes) == [], "authoring classes the model does not name"
    assert sorted(declared_classes - in_code) == [], "model names authoring classes that are gone"


def test_vocabularies_match_literals(model: dict[str, Any]) -> None:
    for vocabulary in model["vocabularies"]:
        annotation = class_fields(ROOT / vocabulary["file"], vocabulary["class"])[vocabulary["field"]]
        assert literal_values(annotation) == set(vocabulary["values"]), (
            f"vocabulary {vocabulary['name']!r} differs from "
            f"{vocabulary['class']}.{vocabulary['field']}"
        )


def test_model_is_internally_consistent(model: dict[str, Any]) -> None:
    processes = {p["name"]: p for p in model["processes"]}
    assert len(processes) == len(model["processes"]), "duplicate process names"
    entities = {e["name"] for e in model["entities"]}
    assert len(entities) == len(model["entities"]), "duplicate entity names"
    records = {r["name"]: r for r in model["records"]}
    assert len(records) == len(model["records"]), "duplicate record names"
    for process in processes.values():
        for name in process.get("writes", []):
            assert name in records, f"process {process['name']} writes undeclared record {name!r}"
        for name in process.get("changes", []):
            assert name in entities, f"process {process['name']} changes undeclared entity {name!r}"
    for record in records.values():
        for name in record.get("written_by", []):
            assert name in processes, f"record {record['name']} names unknown process {name}"
            assert record["name"] in processes[name].get("writes", []), (
                f"process {name} does not list record {record['name']}"
            )


def test_view_coverage_names_only_declared_elements(model: dict[str, Any]) -> None:
    views = {v["name"] for v in model["views"]}
    names = (
        {e["name"] for e in model["entities"]}
        | {p["name"] for p in model["processes"]}
        | {r["name"] for r in model["records"]}
    )
    rows = [row["element"] for row in model["coverage"]]
    assert len(rows) == len(set(rows)), "duplicate coverage rows"
    assert sorted(set(rows) - names) == [], "coverage rows name undeclared elements"
    assert sorted({e["name"] for e in model["entities"]} - set(rows)) == [], "entities without a coverage row"
    assert sorted({r["name"] for r in model["records"]} - set(rows)) == [], "records without a coverage row"
    text = COVERAGE_PATH.read_text(encoding="utf-8")
    for row in model["coverage"]:
        assert set(row["views"]) == views, f"coverage row {row['element']!r} must give every view"
        for view, value in row["views"].items():
            assert value in COVERAGE_VALUES, f"{row['element']} / {view}: {value!r}"
        assert f"| {row['element']} |" in text, f"VIEW_COVERAGE.md has no row for {row['element']}"
    for gap in model["gaps"]:
        assert f"### {gap['id']}." in text, f"gap {gap['id']} is not described in VIEW_COVERAGE.md"
        assert gap.get("status") in {"open", "fixed"}, f"gap {gap['id']} needs status open or fixed"
