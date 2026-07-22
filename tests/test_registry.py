import pytest

from faultline.exceptions import DataIntegrityError
from faultline.registry import ErrorCatalog


def test_register_and_lookup():
    catalog = ErrorCatalog()

    @catalog.register(code="TEST-001", remediation="Do the thing")
    class SampleError(DataIntegrityError):
        """A sample error for testing."""

    spec = catalog.spec_for(SampleError)
    assert spec is not None
    assert spec.code == "TEST-001"
    assert spec.remediation == "Do the thing"
    assert spec.category == "DataIntegrityError"


def test_duplicate_code_rejected():
    catalog = ErrorCatalog()

    @catalog.register(code="TEST-002", remediation="")
    class FirstError(DataIntegrityError):
        pass

    with pytest.raises(ValueError):

        @catalog.register(code="TEST-002", remediation="")
        class SecondError(DataIntegrityError):
            pass


def test_rejects_non_toolchain_exceptions():
    catalog = ErrorCatalog()

    with pytest.raises(TypeError):

        @catalog.register(code="TEST-003", remediation="")
        class NotAToolchainError(Exception):
            pass


def test_retryable_override():
    catalog = ErrorCatalog()

    @catalog.register(code="TEST-004", remediation="", retryable=False)
    class UnsafeToRetryError(DataIntegrityError):
        pass

    spec = catalog.spec_for(UnsafeToRetryError)
    assert spec is not None
    assert spec.retryable is False
    assert UnsafeToRetryError.retryable is False


def test_class_for_code_reverse_lookup():
    catalog = ErrorCatalog()

    @catalog.register(code="TEST-005", remediation="")
    class SomeError(DataIntegrityError):
        pass

    assert catalog.class_for_code("TEST-005") is SomeError
    assert catalog.class_for_code("NOPE") is None


def test_all_specs_sorted_by_code():
    catalog = ErrorCatalog()

    @catalog.register(code="TEST-020", remediation="")
    class BError(DataIntegrityError):
        pass

    @catalog.register(code="TEST-010", remediation="")
    class AError(DataIntegrityError):
        pass

    codes = [spec.code for spec in catalog.all_specs()]
    assert codes == ["TEST-010", "TEST-020"]
