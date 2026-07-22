import json
import logging
from pathlib import Path

import pytest

from faultline.diagnostics import BundleWriter, recording
from faultline.exceptions import InternalError


def test_no_bundle_written_on_success(tmp_path: Path):
    writer = BundleWriter(output_dir=tmp_path)
    logger = logging.getLogger("test.success")

    with recording(logger=logger, bundle_writer=writer):
        logger.debug("everything is fine")

    assert list(tmp_path.glob("*")) == []


def test_bundle_written_on_failure(tmp_path: Path):
    writer = BundleWriter(output_dir=tmp_path)
    logger = logging.getLogger("test.failure")

    with pytest.raises(InternalError):
        with recording(logger=logger, bundle_writer=writer):
            logger.debug("about to fail")
            raise InternalError("boom", context={"stage": "unit-test"})

    bundles = list(tmp_path.glob("*"))
    assert len(bundles) == 1

    manifest = json.loads((bundles[0] / "manifest.json").read_text())
    assert manifest["error"]["message"] == "boom"
    assert manifest["error"]["context"]["stage"] == "unit-test"

    log_contents = (bundles[0] / "recent.log").read_text()
    assert "about to fail" in log_contents


def test_debug_logs_are_captured_even_when_logger_level_is_higher(tmp_path: Path):
    """Regression test: a handler's own DEBUG level does nothing if the
    logger itself discards debug records first. `recording()` must widen
    the logger's effective level for its duration, or debug-level context
    silently vanishes from every diagnostic bundle."""
    writer = BundleWriter(output_dir=tmp_path)
    logger = logging.getLogger("test.higher-level")
    logger.setLevel(logging.WARNING)  # simulate a normally-quiet logger

    with pytest.raises(InternalError):
        with recording(logger=logger, bundle_writer=writer):
            logger.debug("this debug line must survive into the bundle")
            raise InternalError("boom")

    bundle = next(tmp_path.glob("*"))
    log_contents = (bundle / "recent.log").read_text()
    assert "this debug line must survive into the bundle" in log_contents
    # level must be restored afterwards, not left widened permanently
    assert logger.level == logging.WARNING


def test_correlation_id_is_yielded_and_reused(tmp_path: Path):
    writer = BundleWriter(output_dir=tmp_path)
    logger = logging.getLogger("test.correlation")

    with pytest.raises(InternalError):
        with recording(logger=logger, bundle_writer=writer, correlation_id="fixed-id") as cid:
            assert cid == "fixed-id"
            raise InternalError("boom")

    bundle_dirs = list(tmp_path.glob("*fixed-id*"))
    assert len(bundle_dirs) == 1
