from urllib.parse import urlencode
from mock import MagicMock
import pytest
from pytest_mock import MockerFixture
from RPA.MSGraph import MSGraph, DEFAULT_REDIRECT_URI, PermissionBundle
from pathlib import Path

RESOURCE_DIR = Path(__file__).parent / "resources"
CONFIG_FILE = RESOURCE_DIR / "msgraph"

DEFAULT_STATE = "123"
MOCK_CLIENT_ID = "my-client-id"
MOCK_CLIENT_SECRET = "my-client-secret"
MOCK_AUTH_CODE = "my-user-auth-code"
MOCK_ACCESS_TOKEN = "microsoft-access-token-{:0>2}"
MOCK_REFRESH_TOKEN = "microsoft-refresh-token-{:0>2}"


@pytest.fixture
def library() -> MSGraph:
    return MSGraph()


@pytest.fixture
def configured_library(library: MSGraph) -> MSGraph:
    library.configure_msgraph_client(MOCK_CLIENT_ID, MOCK_CLIENT_SECRET)
    return library


@pytest.fixture
def init_auth(library: MSGraph, mocker: MockerFixture) -> str:
    config = {"token_urlsafe.return_value": DEFAULT_STATE}
    mocker.patch("RPA.MSGraph.secrets", **config)
    return library.generate_oauth_authorize_url(MOCK_CLIENT_ID, MOCK_CLIENT_SECRET)


def _patch_token_response(
    mocker: MockerFixture, iteration: int
) -> MockerFixture._Patcher:
    mock_token_response = MagicMock()
    mock_token_response.status_code = 200
    mock_token_response.headers = {"Content-Type": "application/json"}
    mock_token_response.json.return_value = {
        "token_type": "Bearer",
        "scope": "%20F".join(PermissionBundle.BASIC.value),
        "expires_in": 3600,
        "access_token": MOCK_ACCESS_TOKEN.format(iteration),
        "refresh_token": MOCK_REFRESH_TOKEN.format(iteration),
    }
    config = {"post.return_value": mock_token_response}
    return mocker.patch("microsoftgraph.client.requests", **config)


def test_configuring_graph_client(library: MSGraph, mocker: MockerFixture) -> None:
    mock_client = mocker.patch("RPA.MSGraph.Client", autospec=True)

    library.generate_oauth_authorize_url(MOCK_CLIENT_ID, MOCK_CLIENT_SECRET)

    mock_client.assert_any_call(MOCK_CLIENT_ID, MOCK_CLIENT_SECRET)


def test_generating_auth_url(init_auth: str) -> None:
    params = {
        "client_id": MOCK_CLIENT_ID,
        "redirect_uri": DEFAULT_REDIRECT_URI,
        "scope": " ".join(PermissionBundle.BASIC.value),
        "response_type": "code",
        "response_mode": "query",
        "state": DEFAULT_STATE,
    }

    assert (
        f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{urlencode(params)}"
        == init_auth
    )


def test_auth_cycle(library: MSGraph, mocker: MockerFixture, init_auth: str) -> None:
    _patch_token_response(mocker, 1)

    refresh_token = library.authorize_and_get_token(MOCK_AUTH_CODE)

    assert library.user_token.data["access_token"] == MOCK_ACCESS_TOKEN.format(1)
    assert refresh_token == MOCK_REFRESH_TOKEN.format(1)


def test_refreshing_token(configured_library: MSGraph, mocker: MockerFixture) -> None:
    _patch_token_response(mocker, 2)

    refresh_token = configured_library.refresh_oauth_token(MOCK_REFRESH_TOKEN.format(1))

    assert configured_library.user_token.data[
        "access_token"
    ] == MOCK_ACCESS_TOKEN.format(2)
    assert refresh_token == MOCK_REFRESH_TOKEN.format(2)
