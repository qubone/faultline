from faultline.exceptions import InfrastructureError, UserError


def test_user_error_exit_code():
    err = UserError("missing config file", context={"path": "config.yml"})
    assert err.exit_code == 2
    assert err.context["path"] == "config.yml"


def test_infrastructure_error_is_retryable_by_default():
    err = InfrastructureError("REST call timed out")
    assert err.retryable is True


def test_to_dict_roundtrip():
    err = UserError("bad input", remediation="Fix your input file")
    payload = err.to_dict()
    assert payload["error_class"] == "UserError"
    assert payload["remediation"] == "Fix your input file"
    assert payload["exit_code"] == 2


def test_str_returns_message():
    err = UserError("something went wrong")
    assert str(err) == "something went wrong"
