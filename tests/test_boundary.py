import json
from pathlib import Path

import pytest

from faultline.boundary import run_main
from faultline.exceptions import UserError


def test_user_error_exits_with_code_2(tmp_path: Path):
    summary_path = tmp_path / "summary.json"

    def failing():
        raise UserError("missing file", remediation="Check the path", context={"path": "x"})

    with pytest.raises(SystemExit) as exc_info:
        run_main(failing, ci_summary_path=summary_path)

    assert exc_info.value.code == 2
    payload = json.loads(summary_path.read_text())
    assert payload["error_class"] == "UserError"
    assert payload["remediation"] == "Check the path"


def test_unexpected_exception_exits_with_code_1(tmp_path: Path):
    summary_path = tmp_path / "summary.json"

    def failing():
        raise RuntimeError("something nobody classified")

    with pytest.raises(SystemExit) as exc_info:
        run_main(failing, ci_summary_path=summary_path)

    assert exc_info.value.code == 1
    payload = json.loads(summary_path.read_text())
    assert payload["unexpected"] is True


def test_success_passes_through_return_value():
    assert run_main(lambda: 42) == 42
