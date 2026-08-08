from superagent.infrastructure.http_client import normalize_provider_base_url


def test_provider_base_url_accepts_server_root() -> None:
    assert normalize_provider_base_url("http://127.0.0.1:8080") == "http://127.0.0.1:8080"


def test_provider_base_url_accepts_v1_prefix() -> None:
    assert normalize_provider_base_url("http://127.0.0.1:8080/v1") == "http://127.0.0.1:8080"


def test_provider_base_url_accepts_api_v1_prefix() -> None:
    assert normalize_provider_base_url("http://127.0.0.1:8080/api/v1/") == "http://127.0.0.1:8080"
