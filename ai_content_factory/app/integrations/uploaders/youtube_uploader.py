from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.integrations.uploaders.base import UploadResponse, Uploader
from app.logger import get_logger
from app.models import ChannelConfig, VideoMetadata
from app.utils import read_json_file, unique_strings

YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
DEFAULT_SHORTS_HASHTAGS = ("#techfacts", "#shorts", "#didyouknow")


def normalize_hashtag(value: str) -> str:
    hashtag = value.strip()
    if not hashtag:
        return ""
    if not hashtag.startswith("#"):
        hashtag = f"#{hashtag}"
    return hashtag.replace(" ", "")


def build_youtube_hashtags(metadata: VideoMetadata) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in [*metadata.hashtags, *DEFAULT_SHORTS_HASHTAGS]:
        hashtag = normalize_hashtag(value)
        if not hashtag:
            continue
        key = hashtag.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(hashtag)
    return unique_strings(normalized)


def build_youtube_description(metadata: VideoMetadata) -> str:
    description = metadata.description.strip()
    hashtags = build_youtube_hashtags(metadata)
    if not hashtags:
        return description
    if description:
        return f"{description}\n\n{' '.join(hashtags)}"
    return " ".join(hashtags)


def load_upload_metadata(metadata_path: Path | None, fallback: VideoMetadata) -> VideoMetadata:
    if metadata_path is None:
        return fallback
    payload = read_json_file(metadata_path, default=None)
    if not payload:
        return fallback
    return VideoMetadata.model_validate(payload)


class YouTubeUploader(Uploader):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger(self.__class__.__name__)

    def upload(
        self,
        *,
        channel: ChannelConfig,
        video_path: Path,
        metadata: VideoMetadata,
        metadata_path: Path | None = None,
    ) -> UploadResponse:
        upload_metadata = load_upload_metadata(metadata_path, metadata)
        credentials = self._load_credentials()
        youtube = self._build_client(credentials)

        self.logger.info("Uploading %s to YouTube for channel %s", video_path.name, channel.channel_id)
        request = youtube.videos().insert(
            part="snippet,status",
            body=self._build_video_resource(channel=channel, metadata=upload_metadata),
            media_body=self._create_media_upload(video_path),
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status is not None:
                self.logger.info(
                    "YouTube upload progress for %s: %.1f%%",
                    channel.channel_id,
                    status.progress() * 100,
                )

        video_id = response.get("id")
        if not video_id:
            raise RuntimeError(f"YouTube upload completed without video id: {response!r}")

        url = f"https://www.youtube.com/watch?v={video_id}"
        self.logger.info("YouTube upload completed for %s: %s", channel.channel_id, url)
        return UploadResponse(platform="youtube", upload_id=video_id, status="uploaded", url=url)

    def _build_video_resource(self, *, channel: ChannelConfig, metadata: VideoMetadata) -> dict[str, object]:
        hashtags = build_youtube_hashtags(metadata)
        return {
            "snippet": {
                "title": metadata.title.strip()[:100],
                "description": build_youtube_description(metadata),
                "tags": [tag.lstrip("#") for tag in hashtags],
                "categoryId": self.settings.youtube_category_id,
                "defaultLanguage": channel.language,
                "defaultAudioLanguage": channel.language,
            },
            "status": {
                "privacyStatus": self.settings.youtube_privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

    def _load_credentials(self):
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Google API client packages are missing. Run `python -m pip install -r requirements.txt`."
            ) from exc

        client_secrets_path = self.settings.youtube_client_secrets_path
        if not client_secrets_path.exists():
            raise FileNotFoundError(
                "YouTube OAuth client secrets file was not found at "
                f"{client_secrets_path}. Create a Desktop OAuth client in Google Cloud and save the JSON there."
            )

        token_path = self.settings.youtube_token_path
        credentials = None
        if token_path.exists():
            credentials = Credentials.from_authorized_user_file(str(token_path), [YOUTUBE_UPLOAD_SCOPE])

        if credentials and credentials.valid:
            return credentials

        if credentials and credentials.expired and credentials.refresh_token:
            self.logger.info("Refreshing stored YouTube OAuth token.")
            credentials.refresh(Request())
        else:
            self.logger.info("Starting local OAuth flow for YouTube upload access.")
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), [YOUTUBE_UPLOAD_SCOPE])
            credentials = flow.run_local_server(
                host="localhost",
                port=self.settings.youtube_oauth_port,
                open_browser=True,
                authorization_prompt_message=(
                    "Authorize YouTube upload access in the browser window that just opened."
                ),
                success_message="YouTube upload access granted. You can close this tab now.",
            )

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(credentials.to_json(), encoding="utf-8")
        return credentials

    def _build_client(self, credentials):
        try:
            from googleapiclient.discovery import build
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "google-api-python-client is missing. Run `python -m pip install -r requirements.txt`."
            ) from exc

        return build("youtube", "v3", credentials=credentials, cache_discovery=False)

    def _create_media_upload(self, video_path: Path):
        try:
            from googleapiclient.http import MediaFileUpload
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "google-api-python-client is missing. Run `python -m pip install -r requirements.txt`."
            ) from exc

        return MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True, chunksize=8 * 1024 * 1024)
