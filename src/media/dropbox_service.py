import dropbox
from dropbox.exceptions import ApiError
from dropbox.files import WriteMode, UploadSessionCursor, CommitInfo
from fastapi import UploadFile

CHUNK_SIZE = 4 * 1024 * 1024  # 4MB


class DropboxStorageService:

    def __init__(
        self,
        refresh_token: str,
        app_key: str,
        app_secret: str,
    ):
        self.client = dropbox.Dropbox(
            oauth2_refresh_token=refresh_token,
            app_key=app_key,
            app_secret=app_secret,
        )

    # ---------- PUBLIC METHODS ----------

    async def upload_file(
        self,
        file: UploadFile,
        dropbox_path: str,
    ) -> str:
        """
        Upload file and return streaming url
        """

        await self._upload_session(file, dropbox_path)

        return self.get_or_create_shared_link(dropbox_path)

    def get_or_create_shared_link(self, path: str) -> str:
        """
        Idempotent shared link getter
        """

        try:
            link = self.client.sharing_create_shared_link_with_settings(path)
            url = link.url

        except ApiError as e:

            if (
                isinstance(
                    e.error,
                    dropbox.sharing.CreateSharedLinkWithSettingsError
                )
                and e.error.is_shared_link_already_exists()
            ):
                links = self.client.sharing_list_shared_links(
                    path=path,
                    direct_only=True
                )

                if not links.links:
                    raise RuntimeError(
                        f"No shared link found for {path}"
                    )

                url = links.links[0].url

            else:
                raise

        return self._convert_to_stream_url(url)

    # ---------- PRIVATE METHODS ----------

    async def _upload_session(
        self,
        file: UploadFile,
        dropbox_path: str,
    ):

        first_chunk = await file.read(CHUNK_SIZE)

        session = self.client.files_upload_session_start(first_chunk)

        cursor = UploadSessionCursor(
            session_id=session.session_id,
            offset=len(first_chunk),
        )

        while chunk := await file.read(CHUNK_SIZE):

            self.client.files_upload_session_append_v2(
                chunk,
                cursor,
            )

            cursor.offset += len(chunk)

        commit = CommitInfo(
            path=dropbox_path,
            mode=WriteMode.overwrite,
        )

        self.client.files_upload_session_finish(
            b"",
            cursor,
            commit,
        )

    def _convert_to_stream_url(self, url: str) -> str:

        return (
            url
            .replace("?dl=0", "?raw=1")
            .replace("www.dropbox.com", "dl.dropboxusercontent.com")
        )
