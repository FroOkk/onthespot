import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from _support import TEST_ROOT  # noqa: F401

# librespot ships protobuf files built for the pure-Python runtime.
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

from onthespot import downloader
from onthespot.basemodels import DownloadProfile, ItemStatus, QueueItem
from onthespot.otsconfig import config

TRACK_METADATA = {
    "title": "Showdown",
    "artists": "Pendulum",
    "album_name": "Showdown",
    "length": 327706,
}


class ExistingPlaylistTrackTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ots-existing-m3u-"))
        values = {
            "audio_download_path": str(self.root),
            "create_m3u_file": True,
        }
        real_get = config.get
        for patcher in (
            patch.object(config, "get", side_effect=lambda key, default=None: values[key] if key in values else real_get(key, default)),
            patch.object(downloader.time, "sleep"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

        self.item = QueueItem(
            local_id=1,
            item_service="spotify",
            item_type="track",
            item_id="69d0sDgbueWWHuFjcZd996",
            item_url="https://open.spotify.com/track/69d0sDgbueWWHuFjcZd996",
            parent_category="playlist",
            playlist_name="Road Trip",
            playlist_by="alice",
            playlist_number="7",
            item_status=ItemStatus.DOWNLOADING,
            download_profile=DownloadProfile(id="p1", name="test", format="mp3", bitrate=320),
        )
        self.existing = self.root / "Pendulum - Showdown.mp3"
        self.existing.write_bytes(b"already downloaded")

    def test_existing_playlist_track_is_kept_and_added_to_the_m3u(self):
        handled = downloader.DownloadWorker()._handle_existing_file(
            self.item,
            "spotify",
            "track",
            self.item.item_id,
            TRACK_METADATA,
            object(),
            str(self.root / "Pendulum - Showdown"),
        )

        self.assertTrue(handled)
        self.assertEqual(self.item.item_status, ItemStatus.ALREADY_EXISTS)
        self.assertTrue(self.existing.exists())
        m3u = (self.root / "M3U" / "Road Trip by alice.m3u8").read_text(encoding="utf-8")
        self.assertIn(str(self.existing), m3u)


if __name__ == "__main__":
    unittest.main()
