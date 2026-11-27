"""
A Signal post's updated_at means "last edited" (the sitemap sends it to
Google as the post's lastmod). Reading a post bumps its view counter; that
must not move updated_at (api/routes/signals/signals.py, _keep_edit_date).
"""
import asyncio
from datetime import UTC, datetime

from fastapi import Response

from api.routes.signals.signals import get_signal
from database.pg_models import Signal, User

EDITED = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)


def test_reading_a_post_keeps_its_edit_date(db):
    # 1. A published post last edited on 20 Nov.
    author = User(name="Editor", email="editor@signal.test", password="x", confirm_password="x")
    db.add(author)
    db.flush()
    post = Signal(author_id=author.id, title="The board that said never", slug="board-said-never-test",
                  content="Body", status="published", published_at=EDITED, updated_at=EDITED, view_count=0)
    db.add(post)
    db.flush()
    # 2. Someone reads it twice.
    for _ in range(2):
        asyncio.run(get_signal(str(post.id), Response(), db, None))
    db.refresh(post)
    # 3. Two views counted; the edit date has not moved.
    assert post.view_count == 2
    assert post.updated_at == EDITED
