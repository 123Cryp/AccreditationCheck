"""
GenVM lint rule E022: every contract method must be a plain instance method
with `self` as the first parameter. Never @classmethod/@staticmethod
anywhere in contract.py.

This is checked via static AST inspection rather than at runtime, since the
whole point is to catch the decorator/signature shape itself, independent
of whether the offline stub would happen to tolerate it.
"""
import ast
import os

import conftest  # noqa: F401

_CONTRACT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contract.py"
)

_FORBIDDEN_DECORATORS = {"classmethod", "staticmethod"}


def _decorator_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return None


def _find_contract_class(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Heuristic: the contract class subclasses gl.Contract (or
            # Contract), matching this project's single-contract-class file.
            for base in node.bases:
                base_name = _decorator_name(base) if not isinstance(base, ast.Name) else base.id
                if base_name in ("Contract",):
                    return node
    return None


class TestLintRuleE022:
    def setup_method(self):
        with open(_CONTRACT_PATH, "r") as f:
            self.source = f.read()
        self.tree = ast.parse(self.source)
        self.contract_class = _find_contract_class(self.tree)
        assert self.contract_class is not None, "could not locate the gl.Contract subclass"

    def test_contract_class_was_found(self):
        assert self.contract_class.name == "AccreditationCheck"

    def test_no_classmethod_or_staticmethod_decorators_anywhere(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    name = _decorator_name(decorator)
                    assert name not in _FORBIDDEN_DECORATORS, (
                        f"method {node.name!r} uses forbidden decorator {name!r} "
                        f"(GenVM lint rule E022)"
                    )

    def test_every_method_on_the_contract_class_has_self_first(self):
        for node in self.contract_class.body:
            if isinstance(node, ast.FunctionDef):
                args = node.args.args
                assert len(args) >= 1, f"method {node.name!r} has no parameters at all"
                assert args[0].arg == "self", (
                    f"method {node.name!r} does not take `self` as its first "
                    f"parameter (GenVM lint rule E022)"
                )

    def test_no_bare_module_level_functions_masquerade_as_static_helpers_on_the_class(self):
        # Belt-and-suspenders: confirm none of the module-level pure helper
        # functions were accidentally defined *inside* the contract class
        # body without `self` (which would trip E022 even without an
        # explicit @staticmethod decorator, since Python would still accept
        # it syntactically).
        helper_names = {
            "normalize_id_fragment",
            "text_contains_credential_id",
            "normalize_host",
            "registrable_domain",
            "parse_llm_verdict",
            "build_judgment_prompt",
            "aggregate_verdict",
        }
        class_method_names = {
            node.name for node in self.contract_class.body if isinstance(node, ast.FunctionDef)
        }
        assert helper_names.isdisjoint(class_method_names)
