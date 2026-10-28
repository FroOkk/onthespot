import unittest
from unittest.mock import patch

from _support import TEST_ROOT  # noqa: F401

from onthespot.basemodels import DownloadProfile, ItemStatus, QueueItem
from onthespot.otsconfig import config
from onthespot.utils import format_item_path

PLAYLIST_FORMATTER = "Playlists/{playlist_name} by {playlist_owner}/{playlist_number}. {name} - {artist}"

# Service metadata functions return track data only: no playlist keys.
TRACK_METADATA = {"title": "Showdown", "artists": "Pendulum"}


def _playlist_item(**overrides):
    fields = {
        "local_id": 1,
        "item_service": "spotify",
        "item_type": "track",
        "item_id": "69d0sDgbueWWHuFjcZd996",
        "item_url": "https://open.spotify.com/track/69d0sDgbueWWHuFjcZd996",
        "parent_category": "playlist",
        "playlist_name": "Road Trip",
        "playlist_by": "alice",
        "playlist_number": "7",
        "item_status": ItemStatus.WAITING,
        "download_profile": DownloadProfile(id="p1", name="test", format="mp3", bitrate=320),
    }
    fields.update(overrides)
    return QueueItem(**fields)


class PlaylistPathTests(unittest.TestCase):
    def setUp(self):
        values = {
            "use_playlist_path": True,
            "playlist_path_formatter": PLAYLIST_FORMATTER,
            "illegal_character_replacement": "-",
        }
        real_get = config.get
        patcher = patch(
            "onthespot.utils.config.get",
            side_effect=lambda key, default=None: values[key] if key in values else real_get(key, default),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_playlist_tags_come_from_the_queue_item(self):
        self.assertEqual(
            format_item_path(_playlist_item(), TRACK_METADATA),
            "Playlists/Road Trip by alice/7. Showdown - Pendulum",
        )

    def test_playlist_tags_are_sanitized(self):
        self.assertEqual(
            format_item_path(_playlist_item(playlist_name="AC/DC"), TRACK_METADATA),
            "Playlists/AC-DC by alice/7. Showdown - Pendulum",
        )


if __name__ == "__main__":
    unittest.main()
