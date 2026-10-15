"""Regression tests for finalizing downloaded tracks."""

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

TRACK_ID = "4uLU6hMCjMI75M1A2tKUQC"
METADATA = {"title": "Track", "album_name": "Album", "artists": "Artist", "length": "1000"}
SETTINGS = {
    "raw_media_download": False,
    "download_lyrics": False,
    "embed_cover": False,
    "save_album_cover": False,
    "create_m3u_file": False,
}


class TrackFinalizeTests(unittest.TestCase):
    def setUp(self):
        self._saved = {key: config.get(key) for key in SETTINGS}
        for key, value in SETTINGS.items():
            config.set(key, value)
        self.folder = tempfile.mkdtemp(dir=TEST_ROOT)
        self.final_base = os.path.join(self.folder, "Track")
        for name in ("convert_audio_format", "embed_metadata", "fix_mp3_metadata", "progress_hook"):
            patcher = mock.patch(f"onthespot.downloader.{name}")
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def tearDown(self):
        for key, value in self._saved.items():
            config.set(key, value)

    def _finalize(self, service, target_format, temp_format, temp_bitrate="320k"):
        item = QueueItem(
            local_id=1,
            item_service=service,
            item_type="track",
            item_id=TRACK_ID,
            item_url="",
            parent_category="album",
            item_status=ItemStatus.DOWNLOADING,
            download_profile=DownloadProfile(id="mp3-320", name="MP3", format="mp3", bitrate=320),
            target_format=target_format,
        )
        temp_path = os.path.join(self.folder, "~Track" + temp_format)
        with open(temp_path, "wb") as audio_file:
            audio_file.write(bytes(8192))
        _, final_path = DownloadWorker()._finalize_audio(
            item, dict(METADATA), service, "track", TRACK_ID, None,
            self.final_base, temp_path, temp_format, temp_bitrate,
        )
        return temp_path, final_path

    def test_source_format_keeps_the_downloaded_format(self):
        for service, temp_format in (("deezer", ".flac"), ("apple_music", ".m4a")):
            with self.subTest(service=service):
                self.convert_audio_format.reset_mock()

                temp_path, final_path = self._finalize(service, "", temp_format)

                self.assertEqual(final_path, self.final_base + temp_format)
                self.convert_audio_format.assert_called_once_with(temp_path, final_path, 320, temp_format, False)

    def test_raw_download_keeps_the_downloaded_extension(self):
        config.set("raw_media_download", True)

        temp_path, final_path = self._finalize("deezer", "", ".flac")

        self.assertEqual(final_path, self.final_base + ".flac")
        self.assertTrue(os.path.isfile(final_path))
        self.assertFalse(os.path.exists(temp_path))
        self.convert_audio_format.assert_not_called()


if __name__ == "__main__":
    unittest.main()
