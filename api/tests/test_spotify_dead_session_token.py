"""spotify_get_token must not hand out a session whose socket librespot left closed."""

import os
import socket
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from _support import TEST_ROOT  # noqa: F401

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

from onthespot.api import spotify  # noqa: E402
from onthespot.runtimedata import account_pool  # noqa: E402


def _session(sock):
    """A librespot Session as far as the dead-socket check and re-init look at it."""
    return SimpleNamespace(connection=SimpleNamespace(_ConnectionHolder__socket=sock), close=MagicMock())


class SpotifyGetTokenDeadSessionTests(unittest.TestCase):
    def setUp(self):
        patcher = patch("onthespot.api.spotify.Session")
        self.session_cls = patcher.start()
        self.addCleanup(patcher.stop)
        self.built = self.session_cls.Builder.return_value.stored_file.return_value.create.return_value
        self.sock = socket.socket()
        self.addCleanup(self.sock.close)

    def _token_for(self, session):
        account = {"uuid": "test-dead-session", "username": "tester", "login": {"session": session}}
        account_pool.append(account)
        self.addCleanup(account_pool.remove, account)
        return spotify.spotify_get_token(len(account_pool) - 1), account

    def test_session_with_closed_socket_is_rebuilt(self):
        dead = _session(self.sock)
        self.sock.close()

        token, account = self._token_for(dead)

        dead.close.assert_called_once_with()
        self.assertIs(token, self.built)
        self.assertIs(account["login"]["session"], self.built)

    def test_session_with_open_socket_is_kept(self):
        live = _session(self.sock)

        token, _ = self._token_for(live)

        self.assertIs(token, live)
        live.close.assert_not_called()
        self.session_cls.Builder.assert_not_called()


if __name__ == "__main__":
    unittest.main()
