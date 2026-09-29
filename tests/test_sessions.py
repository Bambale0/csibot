from csibot.sessions import SessionStore


def test_session_store_reset_discards_previous_analysis() -> None:
    store = SessionStore()
    session = store.get(123)
    session.question = "old"
    session.vision_data = {"palace_grid": {}}

    fresh = store.reset(123)

    assert fresh is store.get(123)
    assert fresh.question is None
    assert fresh.vision_data is None
