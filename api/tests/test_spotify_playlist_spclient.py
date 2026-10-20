"""Spotify playlists load through librespot's playlist service, not the Web API.

No network: the librespot session and the playlist fetcher are faked.
"""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from _support import TEST_ROOT  # noqa: F401

# librespot ships protobuf files built for the pure-Python runtime.
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

from librespot.proto import Playlist4External_pb2

from onthespot.api.spotify import spotify_get_playlist
from onthespot.parsingworker import ParsingWorker
from onthespot.resources.exceptions import SpotifyPlaylistUnavailableError
from onthespot.runtimedata import pending

PLAYLIST_ID = "37i9dQZF1DXcBWIGoYBM5M"
PLAYLIST_URL = f"https://open.spotify.com/playlist/{PLAYLIST_ID}"
LIKED_SONGS_URL = "https://open.spotify.com/collection/tracks"
YOUR_EPISODES_URL = "https://open.spotify.com/collection/your-episodes"
TRACK_A = "4uLU6hMCjMI75M1A2tKUQC"
TRACK_B = "7GhIk7Il098yCjg4BQjzvb"
EPISODE = "512ojhOuo1ktJprKbVcKyQ"


def _page(uris, pos=0, truncated=False, name="Road Trip", owner="alice"):
    page = Playlist4External_pb2.SelectedListContent()
    page.length = 10000
    page.owner_username = owner
    page.attributes.name = name
    page.contents.pos = pos
    page.contents.truncated = truncated
    for uri in uris:
        page.contents.items.add(uri=uri)
    return SimpleNamespace(status_code=200, content=page.SerializeToString())


class _FakeApi:
    def __init__(self, responses):
        self.responses = list(responses)
        self.suffixes = []

    def send(self, method, suffix, headers, body):
        self.suffixes.append(suffix)
        return self.responses.pop(0)


class _FakeSession:
    def __init__(self, responses):
        self.fake_api = _FakeApi(responses)

    def api(self):
        return self.fake_api


class SpotifyGetPlaylistTests(unittest.TestCase):
    def test_maps_tracks_and_episodes_and_skips_local_files_keeping_positions(self):
        session = _FakeSession(
            [
                _page(
                    [
                        f"spotify:track:{TRACK_A}",
                        "spotify:local:Artist:Album:Title:215",
                        f"spotify:episode:{EPISODE}",
                    ]
                )
            ]
        )

        name, owner, entries = spotify_get_playlist(session, PLAYLIST_ID)

        self.assertEqual(name, "Road Trip")
        self.assertEqual(owner, "alice")
        self.assertEqual(
            entries, [(1, "track", TRACK_A), (3, "podcast_episode", EPISODE)]
        )
        self.assertEqual(
            session.fake_api.suffixes,
            [f"/playlist/v2/playlist/{PLAYLIST_ID}?from=0&length=1000"],
        )

    def test_pages_until_not_truncated(self):
        session = _FakeSession(
            [
                _page(
                    [f"spotify:track:{TRACK_A}", f"spotify:track:{TRACK_B}"],
                    pos=0,
                    truncated=True,
                ),
                _page([f"spotify:episode:{EPISODE}"], pos=2, truncated=False),
            ]
        )

        _, _, entries = spotify_get_playlist(session, PLAYLIST_ID)

        self.assertEqual(
            entries,
            [
                (1, "track", TRACK_A),
                (2, "track", TRACK_B),
                (3, "podcast_episode", EPISODE),
            ],
        )
        self.assertIn("from=2&length=1000", session.fake_api.suffixes[1])

    def test_not_found_raises_with_status_in_message(self):
        session = _FakeSession([SimpleNamespace(status_code=404, content=b"")])

        with self.assertRaises(SpotifyPlaylistUnavailableError) as ctx:
            spotify_get_playlist(session, PLAYLIST_ID)

        self.assertIn("404", str(ctx.exception))

    def test_unnamed_playlist_falls_back_to_its_id(self):
        session = _FakeSession([_page([f"spotify:track:{TRACK_A}"], name="")])

        name, _, _ = spotify_get_playlist(session, PLAYLIST_ID)

        self.assertEqual(name, PLAYLIST_ID)


class ExpandSpotifyPlaylistTests(unittest.TestCase):
    def setUp(self):
        pending.replace_items([])
        self.addCleanup(pending.replace_items, [])
        self.worker = ParsingWorker()

    def _pending(self):
        return pending.get_items()

    def test_enqueues_one_item_per_entry(self):
        entries = [(1, "track", TRACK_A), (3, "podcast_episode", EPISODE)]
        with patch(
            "onthespot.parsingworker.spotify_get_playlist",
            return_value=("Road Trip", "alice", entries),
        ):
            self.worker._expand_spotify_playlist("token", PLAYLIST_ID, PLAYLIST_URL)

        items = self._pending()
        self.assertEqual(len(items), 2)
        track, episode = items
        self.assertEqual(
            (track.item_type, track.item_id, track.item_url, track.playlist_number),
            ("track", TRACK_A, f"https://open.spotify.com/track/{TRACK_A}", "1"),
        )
        self.assertEqual(
            (
                episode.item_type,
                episode.item_id,
                episode.item_url,
                episode.playlist_number,
            ),
            (
                "podcast_episode",
                EPISODE,
                f"https://open.spotify.com/episode/{EPISODE}",
                "3",
            ),
        )
        for item in items:
            self.assertEqual(item.item_service, "spotify")
            self.assertEqual(item.parent_category, "playlist")
            self.assertEqual(item.playlist_name, "Road Trip")
            self.assertEqual(item.playlist_by, "alice")

    def test_connection_error_reinits_session_and_retries_once(self):
        result = ("Road Trip", "alice", [(1, "track", TRACK_A)])
        with (
            patch(
                "onthespot.parsingworker.spotify_get_playlist",
                side_effect=[ConnectionError("connection reset"), result],
            ) as fetch,
            patch("onthespot.parsingworker.reinit_spotify_session") as reinit,
            patch(
                "onthespot.parsingworker.get_account_token", return_value="fresh-token"
            ) as get_token,
        ):
            self.worker._expand_spotify_playlist(
                "dead-token", PLAYLIST_ID, PLAYLIST_URL
            )

        reinit.assert_called_once_with("dead-token")
        get_token.assert_called_once_with("spotify")
        self.assertEqual(fetch.call_args_list[1].args, ("fresh-token", PLAYLIST_ID))
        self.assertEqual([item.item_id for item in self._pending()], [TRACK_A])

    def test_not_found_does_not_retry_and_enqueues_nothing(self):
        error = SpotifyPlaylistUnavailableError(
            f"HTTP 404 loading playlist {PLAYLIST_ID}"
        )
        with (
            patch(
                "onthespot.parsingworker.spotify_get_playlist", side_effect=error
            ) as fetch,
            patch("onthespot.parsingworker.reinit_spotify_session") as reinit,
            patch.object(ParsingWorker, "_emit_collection_error") as emit,
        ):
            self.worker._expand_spotify_playlist("token", PLAYLIST_ID, PLAYLIST_URL)

        fetch.assert_called_once()
        reinit.assert_not_called()
        emit.assert_called_once_with(
            error, "spotify", "playlist", PLAYLIST_ID, PLAYLIST_URL
        )
        self.assertEqual(self._pending(), [])
