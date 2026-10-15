"""Regression tests for Spotify podcast episode metadata lookups."""

import os
import unittest

from _support import TEST_ROOT  # noqa: F401

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

from librespot.core import ApiClient  # noqa: E402
from librespot.metadata import EpisodeId  # noqa: E402
from librespot.proto import Metadata_pb2 as Metadata  # noqa: E402
from onthespot.api.spotify import _patch_librespot_episode_uri  # noqa: E402

EPISODE_ID = "475WkgQXJtNpZyJAegnOzv"


class _CapturingApiClient:
    """Stands in for ApiClient's HTTP call so the real metadata method can run offline."""

    def __init__(self):
        self.requested_uris = []

    def get_ext_metadata(self, extension_kind, uri):
        self.requested_uris.append(uri)
        return Metadata.Episode(name="Episode").SerializeToString()


class SpotifyEpisodeUriTests(unittest.TestCase):
    def test_episode_uri_uses_the_lowercase_scheme(self):
        uri = EpisodeId.from_base62(EPISODE_ID).to_spotify_uri()

        self.assertEqual(uri, f"spotify:episode:{EPISODE_ID}")

    def test_episode_metadata_lookup_sends_the_lowercase_uri(self):
        api = _CapturingApiClient()

        episode = ApiClient.get_metadata_4_episode(api, EpisodeId.from_base62(EPISODE_ID))

        self.assertEqual(api.requested_uris, [f"spotify:episode:{EPISODE_ID}"])
        self.assertEqual(episode.name, "Episode")

    def test_patch_is_applied_only_once(self):
        patched = EpisodeId.to_spotify_uri

        self.assertTrue(_patch_librespot_episode_uri())
        self.assertIs(EpisodeId.to_spotify_uri, patched)

    def test_patch_is_skipped_when_librespot_already_uses_lowercase(self):
        patched = EpisodeId.to_spotify_uri

        def fixed_to_spotify_uri(self):
            return "spotify:episode:" + patched(self).split(":", 2)[2]

        EpisodeId.to_spotify_uri = fixed_to_spotify_uri
        try:
            self.assertFalse(_patch_librespot_episode_uri())
            self.assertIs(EpisodeId.to_spotify_uri, fixed_to_spotify_uri)
        finally:
            EpisodeId.to_spotify_uri = patched


if __name__ == "__main__":
    unittest.main()
