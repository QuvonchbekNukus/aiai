from __future__ import annotations

from app.config import Settings
from app.models import ChannelConfig
from app.utils import read_json_file


class ChannelService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._channels: list[ChannelConfig] = []

    def load_channels(self) -> list[ChannelConfig]:
        payload = read_json_file(self.settings.channels_file, default=[])
        self._channels = [ChannelConfig.model_validate(item) for item in payload]
        return list(self._channels)

    def reload_channels(self) -> list[ChannelConfig]:
        return self.load_channels()

    def get_channels(self, *, active_only: bool = False) -> list[ChannelConfig]:
        if not self._channels:
            self.load_channels()
        channels = list(self._channels)
        if active_only:
            return [channel for channel in channels if channel.active]
        return channels

    def get_channel(self, channel_id: str) -> ChannelConfig:
        for channel in self.get_channels():
            if channel.channel_id == channel_id:
                return channel
        raise ValueError(f"Unknown channel_id: {channel_id}")

