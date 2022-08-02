from enum import Enum
import logging
import secrets
from typing import Optional
from microsoftgraph.client import Client
from robot.api.deco import keyword

DEFAULT_REDIRECT_URI = "https://login.microsoftonline.com/common/oauth2/nativeclient"


class PermissionBundle(Enum):
    BASIC = ["offline_access", "user.read"]


class MSGraphAuthenticationError(Exception):
    "Error when authentication fails."


class MSGraph:
    """
    The *MSGraph* library wraps the microsoftgraph package, giving robots
    the ability to access the Microsoft Graph API programmatically.

    Oauth Configuration
    -------------------

    Graph's API primarily authenticates via the OAuth 2.0 authorization code grant
    flow or OpenID Connect. This library exposes the OAuth 2.0 flow for robots to
    authenticate on behalf of users. A user must complete an initial authentication
    flow with the help of our `Oauth Graph Example Bot`_.

    For best results, `register an app`_ in Azure AD and configure it as so:

    - The type is "Web App".
    - Redirect URI should be ``https://login.microsoftonline.com/common/oauth2/nativeclient``
    - The app should be a multi-tenant app.
    - ``Accounts in any organizational directory`` is checked.
    - Has relevant permissions enabled, check the `Microsoft Graph permissions reference`_
    for a list of permissions available to MS Graph apps.

    .. TODO: Determine bundles of permissions needed for each keyword in the library.

    .. _Oauth Graph Example Bot: https://robocorp.com/portal/
    .. _register an app: https://portal.azure.com/#view/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/~/RegisteredApps
    .. _Microsoft Graph permissions reference: https://docs.microsoft.com/en-us/graph/permissions-reference


    """

    ROBOT_LIBRARY_SCOPE = "Global"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> None:
        """When importing the library to Robot Framework, you can set the
        ``client_id`` and ``client_secret``.

        :param str client_id: Application client id.
        :param str client_secret: Application client secret.

        """
        self.logger = logging.getLogger(__name__)
        if client_id and client_secret:
            self.client = Client(client_id, client_secret)
        else:
            self.client = None
        if redirect_uri:
            self.redirect_uri = redirect_uri
        else:
            self.redirect_uri = DEFAULT_REDIRECT_URI
        self.user_token: Optional[dict] = user_token
        self.random_state = None

    def _require_client(self):
        if self.client is None:
            raise MSGraphAuthenticationError("The MSGraph client is not configured.")

    def _require_user_token(self):
        if self.user_token is None:
            raise MSGraphAuthenticationError(
                "There is no user access token to authenticate the request, "
                "refresh the token with a refresh token to continue."
            )

    @keyword
    def generate_oauth_authorize_url(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: str = DEFAULT_REDIRECT_URI,
        scope: PermissionBundle = PermissionBundle.BASIC,
    ) -> str:
        """Generates an authorization URL which must be opened
        by the user to complete the OAuth flow.
        """
        self.random_state = secrets.token_urlsafe()
        if not self.client:
            self.configure_msgraph_client(client_id, client_secret)
        return self.client.authorization_url(
            redirect_uri, scope.value, self.random_state
        )

    @keyword
    def configure_msgraph_client(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: Optional[str] = None,
        redirect_uri: str = DEFAULT_REDIRECT_URI,
    ) -> None:
        """Configures the MS Graph client when authorization has
        already been completed previously. If a refresh token is
        known, it can be provided to obtain a current user token
        to authenticate with.
        """
        self.client = Client(client_id, client_secret)
        self.redirect_uri = redirect_uri
        if refresh_token:
            self.user_token = self.refresh_oauth_token(refresh_token)

    @keyword
    def authorize_and_get_token(self, authorization_code: str) -> str:
        # pylint: disable=anomalous-backslash-in-string
        """Exchanges the OAuth authorization code obtained from
        \`Generate OAuth authorize url\` for an access token. This
        library maintains the user access token for current requests
        and returns the refresh token to be stored in a secure location
        (e.g., the Robocorp Control Room Vault).
        """  # noqa: W605
        self._require_client()
        if not self.random_state:
            raise ValueError(
                "You must first generate an authorize URL and obtain an "
                "authorization code via user interaction."
            )
        self.user_token = self.client.exchange_code(
            self.redirect_uri, authorization_code
        )
        return self.user_token.data["refresh_token"]

    @keyword
    def refresh_oauth_token(self, refresh_token: str) -> str:
        """Refreshes the user token using the provided ``refresh_token``.
        The user token is retained in the library and a new
        refresh_token is returned.
        """
        self._require_client()
        self.user_token = self.client.refresh_token(self.redirect_uri, refresh_token)
        return self.user_token.data["refresh_token"]
