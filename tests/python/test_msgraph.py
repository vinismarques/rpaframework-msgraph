from json.encoder import JSONEncoder
import time
from typing import Union
from urllib.parse import parse_qs, urlencode, urlparse
from mock import MagicMock, ANY
import pytest
from pytest_mock import MockerFixture
from RPA.MSGraph import MSGraph, DEFAULT_REDIRECT_URI, PermissionBundle
from pathlib import Path
import re

RESOURCE_DIR = Path(__file__).parent / "resources"
TEMP_DIR = Path(__file__).parent / "temp"
CONFIG_FILE = RESOURCE_DIR / "msgraph"

DEFAULT_STATE = "123"
MOCK_CLIENT_ID = "my-client-id"
MOCK_CLIENT_SECRET = "my-client-secret"
MOCK_AUTH_CODE = "https://localhost/myapp/?code=my-mock-auth-code-123&state={}&session_state=mock-session-state#"
MOCK_ACCESS_TOKEN = "microsoft-access-token-{:0>2}"
MOCK_REFRESH_TOKEN = "microsoft-refresh-token-{:0>2}"


@pytest.fixture
def library() -> MSGraph:
    return MSGraph(file_backend_path=TEMP_DIR)


@pytest.fixture
def configured_lib(library: MSGraph) -> MSGraph:
    library.configure_msgraph_client(MOCK_CLIENT_ID, MOCK_CLIENT_SECRET)
    return library


@pytest.fixture
def init_auth(library: MSGraph, mocker: MockerFixture) -> str:
    return library.generate_oauth_authorization_url(MOCK_CLIENT_ID, MOCK_CLIENT_SECRET)


def _get_stateful_mock_auth_code(init_auth: str) -> str:
    init_query = parse_qs(urlparse(init_auth).query)
    return MOCK_AUTH_CODE.format(init_query["state"][0])


@pytest.fixture
def authorized_lib(
    configured_lib: MSGraph,
    mocker: MockerFixture,
    init_auth: str,
) -> MSGraph:
    _patch_token_response(configured_lib, mocker, 1)
    configured_lib.authorize_and_get_token(_get_stateful_mock_auth_code(init_auth))
    return configured_lib


def _patch_token_response(
    library: MSGraph, mocker: MockerFixture, iteration: int
) -> MockerFixture._Patcher:
    return _patch_graph_response(
        library,
        mocker,
        {
            "token_type": "Bearer",
            "scope": "%20F".join(PermissionBundle.BASIC.value),
            "expires_in": 3600,
            "access_token": MOCK_ACCESS_TOKEN.format(iteration),
            "refresh_token": MOCK_REFRESH_TOKEN.format(iteration),
        },
    )


def _patch_graph_response(
    library: MSGraph, mocker: MockerFixture, return_value: dict
) -> MockerFixture._Patcher:
    mock_graph_response = MagicMock()
    mock_graph_response.status_code = 200
    mock_graph_response.headers = {"Content-Type": "application/json"}
    mock_graph_response.json.return_value = return_value
    mock_graph_response.text = JSONEncoder().encode(return_value)
    config = {"return_value": mock_graph_response}

    return mocker.patch.object(library.client.connection.session, "request", **config)


def test_configuring_graph_client(library: MSGraph, mocker: MockerFixture) -> None:
    mock_client = mocker.patch("RPA.MSGraph.Account", autospec=True)

    library.generate_oauth_authorization_url(MOCK_CLIENT_ID, MOCK_CLIENT_SECRET)

    mock_client.assert_any_call((MOCK_CLIENT_ID, MOCK_CLIENT_SECRET), token_backend=ANY)


def test_generating_auth_url(init_auth: str) -> None:
    params = {
        "response_type": "code",
        "client_id": MOCK_CLIENT_ID,
        "redirect_uri": DEFAULT_REDIRECT_URI,
        "scope": " ".join(PermissionBundle.BASIC.value),
    }
    encoded_params = urlencode(params).replace(r"+", r"\+")
    pattern = re.compile(
        rf"https:\/\/login.microsoftonline.com\/common\/oauth2\/v2.0\/authorize\?{encoded_params}"
        r"&state=[a-zA-Z0-9]*&access_type=offline"
    )
    result = re.match(pattern, init_auth)
    assert result


def test_auth_cycle(
    library: MSGraph,
    mocker: MockerFixture,
    init_auth: str,
) -> None:
    _patch_token_response(library, mocker, 1)

    refresh_token = library.authorize_and_get_token(
        _get_stateful_mock_auth_code(init_auth)
    )

    assert library.token_backend.get_token()[
        "access_token"
    ] == MOCK_ACCESS_TOKEN.format(1)
    assert refresh_token == MOCK_REFRESH_TOKEN.format(1)


def test_refreshing_token(configured_lib: MSGraph, mocker: MockerFixture) -> None:
    return_token = {
        "token_type": "Bearer",
        "expires_in": 3600,
        "access_token": MOCK_ACCESS_TOKEN.format(2),
        "refresh_token": MOCK_REFRESH_TOKEN.format(2),
        "expires_at": time.time() + 3600,
        "scope": "%20F".join(PermissionBundle.BASIC.value),
        "scopes": PermissionBundle.BASIC.value,
    }

    # mock_graph_response = MagicMock(
    #     spec=OAuth2Token, wraps=return_token, **scope_config
    # )
    # mock_graph_response.scope = "%20F".join(PermissionBundle.BASIC.value)
    # mock_graph_response.scopes = PermissionBundle.BASIC.value
    # mock_graph_response.__getitem__.side_effect = return_token.__getitem__
    # mock_graph_response.__iter__.side_effect = return_token.__iter__
    # mock_graph_response.__contains__.side_effect = return_token.__contains__
    # mock_graph_response.keys.side_effect = return_token.keys
    config = {"return_value.refresh_token.return_value": return_token}
    mocker.patch("O365.connection.OAuth2Session", **config)

    refresh_token = configured_lib.refresh_oauth_token(MOCK_REFRESH_TOKEN.format(1))

    assert configured_lib.token_backend.get_token()[
        "access_token"
    ] == MOCK_ACCESS_TOKEN.format(2)
    assert refresh_token == MOCK_REFRESH_TOKEN.format(2)


def test_get_me(authorized_lib: MSGraph, mocker: MockerFixture) -> None:
    data = {
        "businessPhones": ["+1 425 555 0109"],
        "displayName": "Adele Vance",
        "givenName": "Adele",
        "jobTitle": "Retail Manager",
        "mail": "AdeleV@contoso.onmicrosoft.com",
        "mobilePhone": "+1 425 555 0109",
        "officeLocation": "18/2111",
        "preferredLanguage": "en-US",
        "surname": "Vance",
        "userPrincipalName": "AdeleV@contoso.onmicrosoft.com",
        "id": "87d349ed-44d7-43e1-9a83-5f2406dee5bd",
    }
    _patch_graph_response(authorized_lib, mocker, data)

    user_me = authorized_lib.get_me()

    assert str(user_me) == data["displayName"]
    assert user_me.object_id == data["id"]


@pytest.mark.parametrize(
    "search_string,response",
    [
        (
            "adam",
            {
                "@odasta.context": "https://graph.microsoft.com/v1.0/$metadata#users",
                "value": [
                    {
                        "businessPhones": [],
                        "displayName": "Conf Room Adams",
                        "givenName": None,
                        "jobTitle": None,
                        "mail": "Adams@contoso.com",
                        "mobilePhone": None,
                        "officeLocation": None,
                        "preferredLanguage": None,
                        "surname": None,
                        "userPrincipalName": "Adams@contoso.com",
                        "id": "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0",
                    },
                    {
                        "businessPhones": ["425-555-0100"],
                        "displayName": "Adam Administrator",
                        "givenName": "Adam-adm",
                        "jobTitle": None,
                        "mail": None,
                        "mobilePhone": "425-555-0101",
                        "officeLocation": None,
                        "preferredLanguage": "en-US",
                        "surname": "Administrator",
                        "userPrincipalName": "admin@contoso.com",
                        "id": "4562bcc8-c436-4f95-b7c0-4f8ce89dca5e",
                    },
                ],
            },
        ),
        (
            "john",
            {
                "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users",
                "value": [
                    {
                        "businessPhones": ["555-555-0100"],
                        "displayName": "Johnny Apple",
                        "givenName": "John",
                        "jobTitle": "IT Admin",
                        "mail": "j.apple@contoso.com",
                        "mobilePhone": None,
                        "officeLocation": None,
                        "preferredLanguage": None,
                        "surname": None,
                        "userPrincipalName": "j.apple@contoso.com",
                        "id": "6ea91a8d-e32e-41a1-b7bd-d2d185eed123",
                    },
                    {
                        "businessPhones": ["555-123-0100"],
                        "displayName": "John Smith",
                        "givenName": "John",
                        "jobTitle": "BDR",
                        "mail": "j.smith@contoso.com",
                        "mobilePhone": "555-123-0101",
                        "officeLocation": None,
                        "preferredLanguage": "en-US",
                        "surname": "Administrator",
                        "userPrincipalName": "admin@contoso.com",
                        "id": "4562bcc8-c436-4f95-b7c0-4f8ce89dc123",
                    },
                ],
            },
        ),
    ],
)
def test_search_for_users(
    authorized_lib: MSGraph, mocker: MockerFixture, search_string: str, response: dict
) -> None:
    _patch_graph_response(authorized_lib, mocker, response)

    users = authorized_lib.search_for_users(search_string)

    for user in users:
        assert user.display_name in [u["displayName"] for u in response["value"]]
        assert user.user_principal_name in [
            u["userPrincipalName"] for u in response["value"]
        ]
