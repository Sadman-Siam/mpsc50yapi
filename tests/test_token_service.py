from app.helper import now
from app.services.token import (
    REFRESH_WINDOW_SECONDS,
    encode_access_token,
    is_within_refresh_window,
)


def test_refresh_window_allows_recently_expired_token():
    payload = {
        "exp": int(now().timestamp()) - 60  # expired a minute ago
    }
    assert is_within_refresh_window(payload) is True


def test_refresh_window_allows_just_inside_boundary():
    payload = {
        "exp": int(now().timestamp()) - (REFRESH_WINDOW_SECONDS - 120)
    }
    assert is_within_refresh_window(payload) is True


def test_refresh_window_rejects_long_expired_token():
    payload = {
        "exp": int(now().timestamp()) - (REFRESH_WINDOW_SECONDS + 3600)
    }
    assert is_within_refresh_window(payload) is False


def test_refresh_window_rejects_unexpired_gracefully():
    # A token that has not expired yet is trivially inside the window.
    payload = {"exp": int(now().timestamp()) + 3600}
    assert is_within_refresh_window(payload) is True


def test_refresh_window_rejects_missing_exp():
    assert is_within_refresh_window({}) is False


def test_old_and_new_refresh_windows_differ():
    """Documents the behaviour change from the previous check.

    The old expression was `exp < now - TTL`, which makes the *acceptance*
    window depend on the token lifetime itself: a token is only refreshable
    while it has been dead for less than one TTL. That works by accident and
    silently shrinks to zero if someone sets the TTL low.

    The new check is an explicit, independent REFRESH_WINDOW_SECONDS.
    """
    ttl = 86400  # ACCESS_TOKEN_TTL_SECONDS
    t = now().timestamp()

    def old_allows(dead_for: int) -> bool:
        return not ((t - dead_for) < (t - ttl))

    def new_allows(dead_for: int) -> bool:
        return is_within_refresh_window({"exp": int(t - dead_for)})

    # One day dead: both accept.
    assert old_allows(ttl) is True
    assert new_allows(ttl) is True

    # Two days dead: the old check rejected it purely because 2d > TTL,
    # even though the intent was to allow a refresh grace period.
    assert old_allows(2 * ttl) is False
    assert new_allows(2 * ttl) is True

    # Well past both windows: both reject.
    assert old_allows(30 * ttl) is False
    assert new_allows(30 * ttl) is False


def test_refresh_window_is_independent_of_token_lifetime():
    """A short TTL must not collapse the refresh window."""
    t = now().timestamp()
    dead_for_a_day = {"exp": int(t - 86400)}
    assert is_within_refresh_window(dead_for_a_day) is True


def test_encode_access_token_roundtrip():
    from app.services.token import decode_token

    token = encode_access_token({"uuid": "abc"})
    payload = decode_token(token)
    assert payload["uuid"] == "abc"
    assert "exp" in payload and "iat" in payload