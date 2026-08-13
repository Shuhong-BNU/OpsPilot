from opspilot import FoundationInfo, get_foundation_info


def test_backend_foundation_imports_by_package_name() -> None:
    info = get_foundation_info()

    assert isinstance(info, FoundationInfo)
    assert info.service == "opspilot-backend"
    assert info.status == "ok"
    assert info.version == "1.2.1"
