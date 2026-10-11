import ast
from pathlib import Path


def test_layer_imports_preserve_composition_boundary():
    source = Path(__file__).resolve().parents[3] / "src" / "mdm_demo"
    allowed = {
        "domain": {"domain"},
        "application": {"domain", "application"},
        "infrastructure": {"domain", "application", "infrastructure"},
        "presentation": {"application", "presentation"},
    }
    violations = []
    for layer, dependencies in allowed.items():
        for path in (source / layer).rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                imports = []
                if isinstance(node, ast.ImportFrom) and node.module:
                    imports = [node.module]
                elif isinstance(node, ast.Import):
                    imports = [alias.name for alias in node.names]
                for module in imports:
                    if module.startswith("mdm_demo.") and module.split(".")[1] not in dependencies:
                        violations.append(f"{path.relative_to(source)} imports {module}")
                    if layer in {"domain", "application"} and module.split(".")[0] in {
                        "fastapi",
                        "sqlalchemy",
                        "redis",
                    }:
                        violations.append(f"{path.relative_to(source)} imports {module}")
    assert not violations, "\n".join(violations)
