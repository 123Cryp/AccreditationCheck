"""
These tests don't test contract.py logic — they test that the offline
`genlayer` stub itself is hardened correctly per guardrail #4. If any of
these fail, the offline suite as a whole cannot be trusted to catch the
corresponding class of live bug, so these are treated as first-class tests,
not meta-tests to skip.
"""
import conftest  # noqa: F401
import pytest

from genlayer import gl, Address, TreeMap, DynArray


class TestAddressHardening:
    def test_wrapping_an_address_raises_type_error(self):
        addr = Address("0x" + "aa" * 20)
        with pytest.raises(TypeError):
            Address(addr)

    def test_constructing_from_hex_string_works(self):
        addr = Address("0x" + "bb" * 20)
        assert str(addr) == "0x" + "bb" * 20

    def test_constructing_from_bytes_works(self):
        addr = Address(b"\x11" * 20)
        assert str(addr).startswith("0x11")

    def test_constructing_from_invalid_type_raises_type_error(self):
        with pytest.raises(TypeError):
            Address(12345)


class TestDataclassNotExported:
    def test_dataclass_not_in_genlayer_star_export(self):
        import genlayer
        assert "dataclass" not in dir(genlayer)
        assert "dataclass" not in genlayer.__all__


class TestDynArrayConstructionRestrictions:
    def test_zero_arg_construction_raises(self):
        with pytest.raises(TypeError):
            DynArray[str]()

    def test_one_arg_construction_raises(self):
        with pytest.raises(TypeError):
            DynArray[str](["a", "b"])

    def test_inmem_allocate_raises_the_documented_internal_error(self):
        with pytest.raises(TypeError):
            gl.storage.inmem_allocate(DynArray[str])


class TestTreeMapConstructionRestrictions:
    def test_zero_arg_construction_raises(self):
        with pytest.raises(TypeError):
            TreeMap[str, str]()

    def test_one_arg_construction_raises(self):
        with pytest.raises(TypeError):
            TreeMap[str, str]({"a": "b"})

    def test_inmem_allocate_works_for_treemap(self):
        # Unlike DynArray, TreeMap[K, V] via inmem_allocate is documented as
        # working — the stub must NOT raise here.
        container = gl.storage.inmem_allocate(TreeMap[str, str])
        assert container == {}
        container["k"] = "v"
        assert container["k"] == "v"


class TestContractTopLevelZeroInit:
    def test_top_level_dynarray_and_treemap_fields_are_usable_immediately(self):
        class Sample(gl.Contract):
            items: DynArray[str]
            lookup: TreeMap[str, str]

            def __init__(self):
                pass

        instance = Sample()
        assert list(instance.items) == []
        instance.items.append("x")
        assert list(instance.items) == ["x"]

        assert dict(instance.lookup) == {}
        instance.lookup["a"] = "1"
        assert instance.lookup["a"] == "1"
