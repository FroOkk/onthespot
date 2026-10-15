"""Tests for the audio format reported by Spotify downloads."""

import io
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from _support import TEST_ROOT

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

from onthespot.basemodels import DownloadProfile, QueueItem  # noqa: E402
from onthespot.constants import ItemStatus  # noqa: E402
from onthespot.services_middleware import download_spotify  # noqa: E402

TRACK_ID = "4uLU6hMCjMI75M1A2tKUQC"
EPISODE_ID = "475WkgQXJtNpZyJAegnOzv"
AUDIO = b"OggS" + bytes(8192)


class _FakeAudioSource(io.BytesIO):
    def available(self):
        return len(self.getbuffer()) - self.tell()


class SpotifyDownloadFormatTests(unittest.TestCase):
    def setUp(self):
        self.temp_base = os.path.join(tempfile.mkdtemp(dir=TEST_ROOT), "~Audio")
        patcher = mock.patch("onthespot.services_middleware.progress_hook")
        patcher.start()
        self.addCleanup(patcher.stop)

    def _download(self, item_type, item_id):
        source = _FakeAudioSource(AUDIO)
        token = mock.MagicMock()
        token.get_user_attribute.return_value = "premium"
        token.content_feeder.return_value.load.return_value = SimpleNamespace(
            input_stream=SimpleNamespace(size=len(AUDIO), stream=lambda: source),
        )
        item = QueueItem(
            local_id=1,
            item_service="spotify",
            item_type=item_type,
            item_id=item_id,
            item_url="",
            parent_category="album",
            item_status=ItemStatus.DOWNLOADING,
            download_profile=DownloadProfile(id="mp3-320", name="MP3", format="mp3", bitrate=320),
            download_format="mp3",
        )
        default_format, _ = download_spotify(item, item_id, item_type, token, self.temp_base)
        return default_format

    def test_track_is_reported_as_ogg_vorbis(self):
        self.assertEqual(self._download("track", TRACK_ID), ".ogg")
        with open(self.temp_base + ".ogg", "rb") as audio_file:
            self.assertEqual(audio_file.read(), AUDIO)

    def test_episode_keeps_the_mp3_extension(self):
        self.assertEqual(self._download("podcast_episode", EPISODE_ID), ".mp3")


if __name__ == "__main__":
    unittest.main()
