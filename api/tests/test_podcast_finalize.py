"""Regression tests for finalizing downloaded podcast episodes."""

import os
import tempfile
import unittest
from unittest import mock

from _support import TEST_ROOT

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

from onthespot.basemodels import DownloadProfile, QueueItem  # noqa: E402
from onthespot.constants import ItemStatus  # noqa: E402
from onthespot.downloader import DownloadWorker  # noqa: E402
from onthespot.otsconfig import config  # noqa: E402

EPISODE_ID = "475WkgQXJtNpZyJAegnOzv"
METADATA = {"title": "Episode", "album_name": "Show", "artists": "Host", "length": "1000"}
SETTINGS = {
    "raw_media_download": False,
    "download_lyrics": False,
    "embed_cover": False,
    "save_album_cover": False,
    "create_m3u_file": False,
    "podcast_file_format": "mp3",
}


class PodcastFinalizeTests(unittest.TestCase):
    def setUp(self):
        self._saved = {key: config.get(key) for key in SETTINGS}
        for key, value in SETTINGS.items():
            config.set(key, value)
        self.folder = tempfile.mkdtemp(dir=TEST_ROOT)
        self.final_base = os.path.join(self.folder, "Episode")
        self.item = QueueItem(
            local_id=1,
            item_service="spotify",
            item_type="podcast_episode",
            item_id=EPISODE_ID,
            item_url="",
            parent_category="podcast",
            item_status=ItemStatus.DOWNLOADING,
            download_profile=DownloadProfile(id="mp3-320", name="MP3", format="mp3", bitrate=320),
        )
        for name in ("convert_audio_format", "embed_metadata", "fix_mp3_metadata", "progress_hook"):
            patcher = mock.patch(f"onthespot.downloader.{name}")
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def tearDown(self):
        for key, value in self._saved.items():
            config.set(key, value)

    def _downloaded_file(self, header, extension=".ogg"):
        path = os.path.join(self.folder, "~Episode" + extension)
        with open(path, "wb") as audio_file:
            audio_file.write(header + bytes(8192))
        return path

    def _finalize(self, temp_path, temp_format=".ogg"):
        return DownloadWorker()._finalize_audio(
            self.item, dict(METADATA), "spotify", "podcast_episode", EPISODE_ID, None,
            self.final_base, temp_path, temp_format, "160k",
        )

    def test_episode_is_converted_to_the_podcast_format(self):
        temp_path = self._downloaded_file(b"OggS")

        _, final_path = self._finalize(temp_path)

        self.assertEqual(final_path, self.final_base + ".mp3")
        self.convert_audio_format.assert_called_once_with(temp_path, final_path, 320, ".ogg", True)


if __name__ == "__main__":
    unittest.main()
