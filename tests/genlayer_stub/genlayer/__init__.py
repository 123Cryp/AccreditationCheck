"""
Offline stub of the `genlayer` SDK surface, hardened to reproduce the real
GenVM bugs/behaviors documented in ARCHITECTURE.md and DESIGN_DECISIONS.md,
so that offline tests actually catch the same class of mistake a live
transaction would.

Deliberately reproduced real-GenVM behaviors:

  * `Address(some_already_constructed_address)` raises TypeError, matching
    real GenVM's `Address.__init__`, which does not accept another Address
    instance. Only raw bytes-convertible values (e.g. hex strings from
    caller-supplied JSON) may be passed to `Address(...)`.
  * `dataclass` is NOT included in this module's exported surface (i.e. NOT
    re-exported via `from genlayer import *`), matching real GenVM builds.
    Contract code must `from dataclasses import dataclass` explicitly; if
    that import is ever accidentally removed, this stub will fail exactly
    the same way real GenVM does (NameError: name 'dataclass' is not
    defined), rather than silently working offline.
  * `DynArray[T]` and `TreeMap[K, V]` reject ALL direct user construction
    (`DynArray[T](...)`, `DynArray[T]()`, and
    `gl.storage.inmem_allocate(DynArray[T])`), matching the real GenVM
    TypeErrors. A separate internal bypass (`_zero_init_storage_field`) is
    used only by this stub's own top-level-field zero-initialization logic
    inside `gl.Contract.__init_subclass__`/instance construction — never
    reachable from ordinary contract code.
"""

from .gl import gl, Address, TreeMap, DynArray

# NOTE: `dataclass` is intentionally NOT imported or re-exported here.
# `from genlayer import *` in real GenVM builds does not provide it, and
# this stub mirrors that so contract code that forgets the explicit
# `from dataclasses import dataclass` fails offline too, not just live.

__all__ = ["gl", "Address", "TreeMap", "DynArray"]
