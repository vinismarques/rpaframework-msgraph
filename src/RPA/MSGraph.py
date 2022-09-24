import base64
from enum import Enum
import logging
from typing import Optional, Union
from pathlib import Path
from O365 import (
    Account,
    MSGraphProtocol,
    FileSystemTokenBackend,
    directory,
    drive,
    sharepoint,
)
from O365.utils import Token, BaseTokenBackend
from O365.utils.utils import (  # noqa: F401 pylint: disable=unused-import
    ME_RESOURCE,
    USERS_RESOURCE,
    GROUPS_RESOURCE,
    SITES_RESOURCE,
)
from robot.api.deco import keyword


DEFAULT_REDIRECT_URI = "https://login.microsoftonline.com/common/oauth2/nativeclient"
DEFAULT_TOKEN_PATH = Path("/temp")

# Define scopes
DEFAULT_PROTOCOL = MSGraphProtocol()
BASIC_SCOPE = DEFAULT_PROTOCOL.get_scopes_for("basic")


class PermissionBundle(Enum):
    """Permission scopes available for authorization."""

    BASIC = BASIC_SCOPE


class MSGraphAuthenticationError(Exception):
    "Error when authentication fails."


class RobocorpVaultTokenBackend(BaseTokenBackend):
    "A simple Token backend that saves to Robocorp vault"


class MSGraph:
    """
    The *MSGraph* library wraps the `O365 package`_, giving robots
    the ability to access the Microsoft Graph API programmatically.

    OAuth Configuration
    -------------------

    Graph's API primarily authenticates via the OAuth 2.0 authorization code grant
    flow or OpenID Connect. This library exposes the OAuth 2.0 flow for robots to
    authenticate on behalf of users. A user must complete an initial authentication
    flow with the help of our `OAuth Graph Example Bot`_.

    For best results, `register an app`_ in Azure AD and configure it as so:

    - The type is "Web App".
    - Redirect URI should be ``https://login.microsoftonline.com/common/oauth2/nativeclient``
    - The app should be a multi-tenant app.
    - ``Accounts in any organizational directory`` is checked.
    - Has relevant permissions enabled, check the `Microsoft Graph permissions reference`_
    for a list of permissions available to MS Graph apps.

    .. TODO: Determine bundles of permissions needed for each keyword in the library.

    .. _O365 package: https://pypi.org/project/O365
    .. _OAuth Graph Example Bot: https://robocorp.com/portal/
    .. _register an app: https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade
    .. _Microsoft Graph permissions reference: https://docs.microsoft.com/en-us/graph/permissions-reference


    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "Global"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        token: Optional[Token] = None,  # pylint: disable=unused-argument
        refresh_token: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        vault_backend: bool = False,
        vault_secret: Optional[str] = None,
        file_backend_path: Optional[Path] = DEFAULT_TOKEN_PATH,
    ) -> None:
        """When importing the library to Robot Framework, you can set the
        ``client_id`` and ``client_secret``.

        :param str client_id: Application client id.
        :param str client_secret: Application client secret.

        """
        self.logger = logging.getLogger(__name__)
        # TODO: Implement a `TokenBackend` that uses Robocorp vault,
        #       if implemented, returned refresh tokens are unnecessary.
        if not vault_backend:
            self.token_backend = FileSystemTokenBackend(
                file_backend_path, "auth_token.txt"
            )
        elif vault_backend and not vault_secret:
            raise ValueError(
                "Argument vault_secret cannot be blank if vault_backend set to True."
            )
        else:
            raise NotImplementedError(
                "Robocorp vault token backend not yet implemented."
            )
        if client_id and client_secret:
            self.configure_msgraph_client(
                client_id, client_secret, refresh_token, redirect_uri
            )
        else:
            self.client = None
            self.redirect_uri = redirect_uri or DEFAULT_REDIRECT_URI

    def _require_client(self):
        if self.client is None:
            raise MSGraphAuthenticationError("The MSGraph client is not configured.")

    def _require_authentication(self):
        self._require_client()
        if not self.client.is_authenticated:
            raise MSGraphAuthenticationError(
                "The MS Graph client is not authenticated."
            )

    def _get_refresh_token(self):
        """Returns the refresh token using the backend if that backend
        is not the Vault.
        """
        try:
            if isinstance(self.token_backend, FileSystemTokenBackend):
                return self.token_backend.load_token().get("refresh_token")
            else:
                return None
        except AttributeError:
            return None

    def _get_drive_instance(
        self, resource: Optional[str] = None, drive_id: Optional[str] = None
    ) -> drive.Drive:
        """Returns the specified drive if any or the default one if none."""
        storage = self.client.storage(resource=resource)
        if drive_id:
            return storage.get_drive(drive_id)
        else:
            return storage.get_default_drive()

    def _encode_share_url(self, file_url: str) -> str:
        """Encodes the OneDrive file share link to a format supported
        by the Graph API.
        """
        base64_bytes = base64.b64encode(bytes(file_url, "utf-8"))
        base64_string = (
            base64_bytes.decode("utf-8")
            .replace("=", "")
            .replace("/", "_")
            .replace("+", "-")
        )
        return "u!{}".format(base64_string)

    def _get_sharepoint_drive(self, site: sharepoint.Site, drive_id: str = None):
        """Returns the specified SharePoint drive if any or the default one if none."""
        if drive_id:
            return site.get_document_library(drive_id)
        else:
            return site.get_default_document_library()

    @keyword
    def configure_msgraph_client(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: Optional[str] = None,
        redirect_uri: str = DEFAULT_REDIRECT_URI,
    ) -> Union[str, None]:
        """Configures the MS Graph client. If a refresh token is
        known, it can be provided to obtain a current user token
        to authenticate with. A new refresh token is returned
        if one is provided.
        """
        credentials = (client_id, client_secret)
        self.client = Account(credentials, token_backend=self.token_backend)
        self.redirect_uri = redirect_uri
        if refresh_token:
            return self.refresh_oauth_token(refresh_token)
        return None

    @keyword
    def generate_oauth_authorization_url(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: str = None,
        scope: PermissionBundle = PermissionBundle.BASIC,
    ) -> str:
        """Generates an authorization URL which must be opened
        by the user to complete the OAuth flow.
        """
        if redirect_uri is None:
            redirect_uri = (
                self.redirect_uri
                if self.redirect_uri is not None
                else DEFAULT_REDIRECT_URI
            )
        if not self.client:
            self.configure_msgraph_client(
                client_id, client_secret, redirect_uri=redirect_uri
            )
        return self.client.connection.get_authorization_url(
            scope.value,
            redirect_uri,
        )[0]

    @keyword
    def authorize_and_get_token(self, authorization_url: str) -> str:
        # pylint: disable=anomalous-backslash-in-string
        """Exchanges the OAuth authorization URL obtained from
        \`Generate OAuth Authorization URL\` for an access token. This
        library maintains the user access token for current requests
        and returns the refresh token to be stored in a secure location
        (e.g., the Robocorp Control Room Vault).
        """  # noqa: W605
        self._require_client()
        if self.client.connection.request_token(
            authorization_url, redirect_uri=self.redirect_uri
        ):
            self.logger.info("Authentication successful.")
            return self._get_refresh_token()
        else:
            raise MSGraphAuthenticationError(
                f"Authentication not successful using '{authorization_url}' as auth URL."  # noqa: E501
            )

    @keyword
    def refresh_oauth_token(self, refresh_token: Optional[str] = None) -> str:
        """Refreshes the user token using the provided ``refresh_token``.
        The user token is retained in the library and a new
        refresh token is returned. If no token is provided, this keyword
        assumes the Robocorp Vault is being used as a backend and attempts
        to refresh it based on that backend.
        """
        self._require_client()
        if refresh_token:
            self.token_backend.token = Token(refresh_token=refresh_token)
            self.token_backend.save_token()
        if self.client.connection.refresh_token():
            self.logger.info("Token successfully refreshed.")
            return self._get_refresh_token()
        else:
            raise MSGraphAuthenticationError("Access token could not be refreshed.")

    @keyword
    def get_me(self) -> directory.User:
        """Returns the MS Graph object representing the currently logged
        in user. A User object is returned. Properties of the user can
        be accessed like so:

        .. code-block: robotframework

            *** Tasks ***
            Get the me object
                ${me}=    Get Me
                ${full_name}=    Set variable    ${me.full_name}
        """
        self._require_authentication()
        return self.client.get_current_user()

    @keyword
    def search_for_users(
        self, search_string: str, resource: str = USERS_RESOURCE
    ) -> list[directory.User]:
        # pylint: disable=anomalous-backslash-in-string
        """Returns a list of user objects from the Active Directory
        based on the provided search string.

        User objects have additional properties that can be accessed
        with dot-notation, see \`Get Me\` for additional details.
        """  # noqa: W605
        self._require_authentication()
        active_directory = self.client.directory(resource)
        query = active_directory.new_query().search(search_string)
        return active_directory.get_users(query=query)

    @keyword
    def list_files_in_onedrive_folder(
        self,
        folder_path: str,
        resource: Optional[str] = None,
        drive_id: Optional[str] = None,
    ) -> list[drive.DriveItem]:
        """Returns a list of files from the specified OneDrive folder.

        The files returned are DriveItem objects and they have additional
        properties that can be accessed with dot-notation.

        :param str folder_path: Path of the folder in OneDrive.
        :param str resource: Name of the resource if not using default.
        :param str drive_id: Drive ID if not using default.
        :return: List of DriveItems in the folder.

        .. code-block: robotframework

            *** Tasks ***
            List files
                ${files}=    List Files In Onedrive Folder    /path/to/folder
                ${file}=    Get From List    ${files}    0
                ${file_name}=    Set Variable    ${file.name}
        """
        self._require_authentication()
        drive_instance = self._get_drive_instance(resource, drive_id)
        folder = drive_instance.get_item_by_path(folder_path)
        items = folder.get_items()
        files = [item for item in items if not item.is_folder]
        return files

    @keyword
    def download_file_from_onedrive(
        self,
        file_path: str,
        target_directory: Optional[str] = None,
        resource: Optional[str] = None,
        drive_id: Optional[str] = None,
    ) -> bool:
        """Downloads a file from OneDrive.

        The downloaded file will be saved to a local path.

        :param str file_path: The file path of the source file.
        :param str target_directory: Destination of the downloaded file,
                defaults to current directory.
        :param str resource: Name of the resource if not using default.
        :param str drive_id: Drive ID if not using default.
        :return: Boolean indicating if download was successful.

        .. code-block: robotframework

            *** Tasks ***
            Download file
                ${success}=    Download File From Onedrive
                ...    /path/to/onedrive/file
                ...    /path/to/local/folder
        """
        self._require_authentication()
        drive_instance = self._get_drive_instance(resource, drive_id)
        file_instance = drive_instance.get_item_by_path(file_path)
        return file_instance.download(to_path=target_directory)

    @keyword
    def find_onedrive_file(
        self,
        search_string: str,
        resource: Optional[str] = None,
        drive_id: Optional[str] = None,
    ) -> list[drive.DriveItem]:
        # pylint: disable=anomalous-backslash-in-string
        """Returns a list of files found in OneDrive based on the search string.

        The files returned are DriveItem objects and they have additional
        properties that can be accessed with dot-notation, see
        \`List Files In Onedrive Folder\` for details.

        :param str search_string: String used to search for file in OneDrive.
        :param str resource: Name of the resource if not using default.
        :param str drive_id: Drive ID if not using default.
        :return: List of DriveItems found based on the search string.

        .. code-block: robotframework

            *** Tasks ***
            Find file
                ${files}=    Find Onedrive File    Report.xlsx
                ${file}=    Get From List    ${files}    0
        """  # noqa: W605
        self._require_authentication()
        drive_instance = self._get_drive_instance(resource, drive_id)
        items = drive_instance.search(search_string)
        files = [item for item in items if not item.is_folder]
        return files

    @keyword
    def download_onedrive_file_from_share_link(
        self,
        share_url: str,
        target_directory: Optional[str] = None,
        resource: Optional[str] = None,
        drive_id: Optional[str] = None,
    ) -> bool:
        # pylint: disable=protected-access
        """Downloads file from the specified OneDrive share link.

        The downloaded file will be saved to a local path.

        :param str share_url: The URL of the shared file
        :param str target_directory: Destination of the downloaded file,
                defaults to current directory.
        :param str resource: Name of the resource if not using default.
        :param str drive_id: Drive ID if not using default.

        .. code-block: robotframework

            *** Tasks ***
            Download file
                ${success}=    Download Onedrive File From Share Link
                ...    https://...
                ...    /path/to/local/folder
        """
        self._require_authentication()
        drive_instance = self._get_drive_instance(resource, drive_id)

        # O365 doesn't support getting items from shared links yet
        base_url = self.client.protocol.service_url
        base_url = base_url[:-1] if base_url.endswith("/") else base_url
        encoded_url = self._encode_share_url(share_url)
        endpoint = "/shares/{id}/driveItem"
        direct_url = "{}{}".format(base_url, endpoint.format(id=encoded_url))

        response = self.client.con.get(direct_url)
        if not response:
            return None

        data = response.json()

        # Everything received from cloud must be passed as self._cloud_data_key
        file_instance = drive_instance._classifier(data)(
            parent=drive_instance, **{drive_instance._cloud_data_key: data}
        )

        return file_instance.download(to_path=target_directory)

    @keyword
    def upload_file_to_onedrive(
        self,
        file_path: str,
        folder_path: str,
        resource: Optional[str] = None,
        drive_id: Optional[str] = None,
    ) -> drive.DriveItem:
        # pylint: disable=anomalous-backslash-in-string
        """Uploads a file to the specified OneDrive folder.

        :param str file_path: Path of the local file being uploaded.
        :param str folder_path: Path of the folder in OneDrive.
        :param str resource: Name of the resource if not using default.
        :param str drive_id: Drive ID if not using default.

        .. code-block: robotframework

            *** Tasks ***
            Upload file
                ${files}=    Upload File To Onedrive
                ...    /path/to/file.txt
                ...    /path/to/folder
        """  # noqa: W605
        self._require_authentication()
        drive_instance = self._get_drive_instance(resource, drive_id)
        folder = drive_instance.get_item_by_path(folder_path)
        return folder.upload_file(item=file_path)

    @keyword
    def get_sharepoint_site(
        self, *args: tuple[str], resource: Optional[str] = SITES_RESOURCE
    ) -> sharepoint.Site:
        """Returns a SharePoint site.

        :param args: It accepts multiple ways of retrieving a site. See below.

         get_site(host_name): the host_name e.g. 'contoso.sharepoint.com'
         or 'root'.

         get_site(site_id): the site_id is a comma separated string of
         (host_name, site_collection_id, site_id).

         get_site(host_name, path_to_site): host_name e.g. 'contoso.
         sharepoint.com' and path_to_site is a url path (with a leading slash).

         get_site(host_name, site_collection_id, site_id): a collection of
         (host_name, site_collection_id, site_id).

        :param str resource: Name of the resource if not using default.
        :return: SharePoint Site instance.

        The return is of type Site and it has additional properties
        that can be accessed with dot-notation.

        .. code-block: robotframework

            *** Tasks ***
            Get site
                ${site}=    Get Sharepoint Site    contoso.sharepoint.com
                ${site_name}=    Set Variable    ${site.display_name}
        """
        self._require_authentication()
        sp = self.client.sharepoint(resource=resource)

        return sp.get_site(*args)

    @keyword
    def get_sharepoint_list(
        self,
        list_name: str,
        site: sharepoint.Site,
    ) -> sharepoint.SharepointList:
        # pylint: disable=anomalous-backslash-in-string
        """Returns a sharepoint list based on the display name of the list.

        :param str list_name: Display name of the SharePoint list.
        :param Site site: Site instance obtained from \`Get Sharepoint Site\`.
        :return: SharePoint List found based on the provided list name.

        .. code-block: robotframework

            *** Tasks ***
            Get List
                ${sharepoint_list}=    Get Sharepoint List    My List    ${site}
                ${list_name}=    Set Variable    ${list.name}
                ${description}=    Set Variable    ${list.description}
                ${id}=    Set Variable    ${list.object_id}
                ${creator_name}=    Set Variable    ${list.created_by.display_name}
        """  # noqa: W605
        self._require_authentication()

        return site.get_list_by_name(list_name)

    @keyword
    def create_sharepoint_list(
        self,
        list_data: dict,
        site: sharepoint.Site,
    ) -> sharepoint.SharepointList:
        # pylint: disable=anomalous-backslash-in-string
        """Creates a sharepoint list and returns the instance.

        :param dict list_data: A dict with the data for the new list.
        :param Site site: Site instance obtained from \`Get Sharepoint Site\`.
        :return: SharePoint List that was created.

        List objects have additional properties that can be accessed
        with dot-notation, see \`Get Sharepoint List\` for additional details.

        .. code-block: robotframework

            *** Tasks ***
            Create list
                ${sharepoint_list}=    Create Sharepoint List
                ...    ${list_data}
                ...    ${site}

        """  # noqa: W605
        self._require_authentication()

        return site.create_list(list_data)

    @keyword
    def list_sharepoint_site_drives(self, site: sharepoint.Site) -> list[drive.Drive]:
        # pylint: disable=anomalous-backslash-in-string
        """Get a list of Drives available in the SharePoint Site.

        :param Site site: Site instance obtained from \`Get Sharepoint Site\`.
        :return: A list of Drives present in the SharePoint Site.

        .. code-block: robotframework

            *** Tasks ***
            List SharePoint drives
                ${drives}    List Sharepoint Site Drives    ${site}
                FOR    ${drive}    IN    @{drives}
                    Log    ${drive.name}
                    Log    ${drive.object_id}
                END
        """  # noqa: W605
        self._require_authentication()

        return site.list_document_libraries()

    @keyword
    def list_files_in_sharepoint_site_drive(
        self, site: sharepoint.Site, drive_id: Optional[str] = None
    ) -> list[drive.DriveItem]:
        # pylint: disable=anomalous-backslash-in-string
        """List files in the SharePoint Site drive.

        If the drive_id is not informed, the default Document Library will be used.
        The drive_id can be obtained from the keyword \`List Sharepoint Site Drives\`.

        The files returned are DriveItem objects and they have additional
        properties that can be accessed with dot-notation, see
        \`List Files In Onedrive Folder\` for details.

        :param Site site: Site instance obtained from \`Get Sharepoint Site\`.
        :param str drive_id: The id of the desired drive.
        :return: The list of DriveItems present in the Site Drive.

        .. code-block: robotframework

            *** Tasks ***

            List files in SharePoint drive
                ${files}    List Files In Sharepoint Site Drive    ${site}
                FOR    ${file}    IN    @{files}
                    Log    ${file.name}
                END
        """  # noqa: W605
        self._require_authentication()
        sp_drive = self._get_sharepoint_drive(site, drive_id)

        return sp_drive.get_items()

    @keyword
    def download_file_from_sharepoint(
        self,
        file_path: str,
        site: sharepoint.Site,
        target_directory: Optional[str] = None,
        drive_id: Optional[str] = None,
    ) -> bool:
        # pylint: disable=anomalous-backslash-in-string
        """Downloads file from SharePoint.

        The downloaded file will be saved to a local folder.

        :param str file_path: The file path of the source file.
        :param Site site: Site instance obtained from \`Get Sharepoint Site\`.
        :param str target_directory: Destination of the downloaded file,
                defaults to current directory.
        :param str drive_id: Drive ID if not using default.
        :return: Boolean indicating if download was successful.

        .. code-block: robotframework

            *** Tasks ***
            Download file
                ${success}=    Download File From Sharepoint
                ...    /path/to/sharepoint/file
                ...    ${site}
                ...    /path/to/local/folder
        """  # noqa: W605
        self._require_authentication()
        sp_drive = self._get_sharepoint_drive(site, drive_id)
        file_instance = sp_drive.get_item_by_path(file_path)

        return file_instance.download(to_path=target_directory)
