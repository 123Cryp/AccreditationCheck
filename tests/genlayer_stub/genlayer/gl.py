"""
Core implementation of the offline `genlayer` stub.

This is a TEST DOUBLE, not a reimplementation of GenVM. Its only job is to:
  (a) let contract.py import and run unmodified outside real GenVM, and
  (b) fail in the same specific ways real GenVM fails for the handful of
      documented bugs in ARCHITECTURE.md / DESIGN_DECISIONS.md, so that an
      offline test suite built against this stub actually has predictive
      power about live behavior for those specific issues.

Everything else (fetch results, LLM responses, sender address) is
configurable per-test via `stub_control` below.
"""

import re


# ==========================================================================
# Address — hardened per guardrail: real GenVM's Address.__init__ rejects
# being handed an already-constructed Address instance.
# ==========================================================================

class Address:
    def __init__(self, value):
        if isinstance(value, Address):
            # Matches real GenVM: TypeError: cannot convert 'Address' object to bytes
            raise TypeError("cannot convert 'Address' object to bytes")
        if isinstance(value, (bytes, bytearray)):
            raw = bytes(value)
        elif isinstance(value, str):
            s = value[2:] if value.lower().startswith("0x") else value
            try:
                raw = bytes.fromhex(s)
            except ValueError:
                raise TypeError(f"cannot convert {value!r} to bytes")
        else:
            raise TypeError(f"cannot convert {type(value).__name__!r} object to bytes")
        object.__setattr__(self, "_raw", raw)

    def __str__(self):
        return "0x" + self._raw.hex()

    def __repr__(self):
        return f"Address({str(self)!r})"

    def __eq__(self, other):
        if isinstance(other, Address):
            return self._raw == other._raw
        return NotImplemented

    def __hash__(self):
        return hash(self._raw)


# ==========================================================================
# DynArray / TreeMap — hardened per guardrail: NO direct user construction
# under any circumstance. Only the internal zero-init bypass (used solely by
# Contract's own field-initialization machinery below) may produce a real
# usable container.
# ==========================================================================

class _TreeMapContainer(dict):
    """Usable, dict-backed stand-in for a real GenVM TreeMap[K, V]."""
    pass


class _DynArrayContainer(list):
    """Usable, list-backed stand-in for a real GenVM DynArray[T]."""
    pass


class _StorageAlias:
    """
    What `TreeMap[K, V]` / `DynArray[T]` actually evaluate to. Calling it
    directly (simulating user code trying to construct one) always raises,
    matching the real GenVM TypeErrors documented in ARCHITECTURE.md.
    """

    def __init__(self, name, container_cls, type_args):
        self._name = name
        self._container_cls = container_cls
        self._type_args = type_args

    def __call__(self, *args, **kwargs):
        if len(args) == 0 and len(kwargs) == 0:
            raise TypeError(f"this class can't be created with {self._name}()")
        n_given = len(args) + len(kwargs) + 1  # +1 for the implicit "self"
        raise TypeError(
            f"{self._name}.__init__() takes 1 positional argument but {n_given} were given"
        )

    def _bypass_zero_init(self):
        """
        Internal-only path used exclusively by Contract's top-level-field
        initialization. Not reachable from ordinary contract code (there is
        no public name bound to this method).
        """
        return self._container_cls()

    def __repr__(self):
        return f"{self._name}[{self._type_args!r}]"


class TreeMap:
    def __class_getitem__(cls, item):
        return _StorageAlias("TreeMap", _TreeMapContainer, item)

    def __init__(self, *args, **kwargs):
        raise TypeError("this class can't be created with TreeMap()")


class DynArray:
    def __class_getitem__(cls, item):
        return _StorageAlias("DynArray", _DynArrayContainer, item)

    def __init__(self, *args, **kwargs):
        raise TypeError("this class can't be created with DynArray()")


# ==========================================================================
# Configurable stub state — tests populate this before invoking contract
# methods.
# ==========================================================================

class _StubState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.sender_address = Address("0x" + "11" * 20)
        # url -> str (page text) or an Exception INSTANCE to raise on render
        self.web_pages = {}
        # ordered list of (matcher, response); matcher is a callable(prompt)->bool
        # or a plain substring to look for in the prompt. response is a str or
        # a callable(prompt)->str.
        self.llm_responses = []
        self.default_llm_response = "Unclear"


stub_control = _StubState()


# ==========================================================================
# gl.message
# ==========================================================================

class _MessageNamespace:
    @property
    def sender_address(self):
        return stub_control.sender_address


# ==========================================================================
# gl.nondet.web / gl.nondet
# ==========================================================================

class _WebNamespace:
    def render(self, url, mode="text", **kwargs):
        if url not in stub_control.web_pages:
            raise RuntimeError(
                f"stub: no configured page for url {url!r} — configure via "
                f"stub_control.web_pages[{url!r}] in the test, or this simulates "
                f"fetch_status: inaccessible"
            )
        entry = stub_control.web_pages[url]
        if isinstance(entry, Exception):
            raise entry
        return entry

    def get(self, url, **kwargs):
        return self.render(url, **kwargs)


class _NondetNamespace:
    def __init__(self):
        self.web = _WebNamespace()

    def exec_prompt(self, prompt, **kwargs):
        for matcher, response in stub_control.llm_responses:
            matched = matcher(prompt) if callable(matcher) else (matcher in prompt)
            if matched:
                return response(prompt) if callable(response) else response
        return stub_control.default_llm_response


# ==========================================================================
# gl.eq_principle — offline, there is only one "validator", so we simply
# invoke the callable once and return its result.
# ==========================================================================

class _EqPrincipleNamespace:
    def strict_eq(self, fn):
        return fn()

    def prompt_comparative(self, *args, **kwargs):
        raise NotImplementedError("prompt_comparative is not used by this contract")

    def prompt_non_comparative(self, *args, **kwargs):
        raise NotImplementedError("prompt_non_comparative is not used by this contract")


# ==========================================================================
# gl.vm
# ==========================================================================

class UserError(Exception):
    pass


class _VmNamespace:
    UserError = UserError

    def run_nondet_unsafe(self, leader_fn, validator_fn=None):
        return leader_fn()


# ==========================================================================
# gl.public — method decorators. No-ops functionally; tag the method so
# tests/tooling could introspect method type if ever useful.
# ==========================================================================

class _PublicNamespace:
    @staticmethod
    def view(fn):
        fn._gl_method_type = "view"
        return fn

    @staticmethod
    def write(fn):
        fn._gl_method_type = "write"
        return fn


# ==========================================================================
# gl.storage — hardened per guardrail: inmem_allocate works for TreeMap
# (matching real, documented behavior) but raises the exact GenVM-internal
# TypeError for any DynArray alias, reproducing the confirmed live quirk.
# ==========================================================================

class _StorageNamespace:
    def inmem_allocate(self, alias):
        if isinstance(alias, _StorageAlias):
            if alias._container_cls is _DynArrayContainer:
                raise TypeError(
                    "_GenericAlias.__init__() missing 1 required positional argument: 'args'"
                )
            return alias._bypass_zero_init()
        raise TypeError(f"unsupported type for inmem_allocate: {alias!r}")


# ==========================================================================
# gl.Contract — base class. Top-level DynArray[...]/TreeMap[...,...] fields
# declared as class annotations are zero-initialized automatically (via the
# internal bypass), exactly matching the guardrail: "you only ever .append()
# to it, never construct it yourself."
# ==========================================================================

def _collect_storage_annotations(cls):
    """Walk the MRO collecting __annotations__ that are _StorageAlias values."""
    found = {}
    for klass in reversed(cls.__mro__):
        for name, hint in vars(klass).get("__annotations__", {}).items():
            if isinstance(hint, _StorageAlias):
                found[name] = hint
    return found


class Contract:
    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        for name, alias in _collect_storage_annotations(cls).items():
            object.__setattr__(instance, name, alias._bypass_zero_init())
        return instance


# ==========================================================================
# gl — the single namespace object contract.py imports via `from genlayer
# import *` (re-exported from __init__.py).
# ==========================================================================

class _GL:
    Contract = Contract
    message = _MessageNamespace()
    nondet = _NondetNamespace()
    eq_principle = _EqPrincipleNamespace()
    vm = _VmNamespace()
    public = _PublicNamespace()
    storage = _StorageNamespace()


gl = _GL()
