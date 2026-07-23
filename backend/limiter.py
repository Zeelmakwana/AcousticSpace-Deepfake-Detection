"""
AcousticSpace — SlowAPI Limiter Singleton
==========================================
Defines the single application-wide ``Limiter`` instance.

Why a separate module?
-----------------------
``app.py`` creates the FastAPI application and must attach the limiter to
``app.state.limiter``.  Route modules (e.g. ``auth/routes.py``) need to
import the limiter to use ``@limiter.limit()`` decorators.  If the limiter
were defined inside ``app.py``, both directions would create a circular
import:

    app.py  →  auth/routes.py  →  app.py   ← circular!

Extracting the limiter into this module breaks the cycle:

    app.py        imports from limiter.py   ✓
    auth/routes.py imports from limiter.py  ✓
    limiter.py    imports nothing from app  ✓

Usage
-----
In ``app.py``::

    from limiter import limiter
    app.state.limiter = limiter

In a route module::

    from limiter import limiter

    @router.post("/some-endpoint")
    @limiter.limit("5/minute")
    async def some_endpoint(request: Request, ...):
        ...

The ``request: Request`` parameter **must** be present in every rate-limited
route handler — SlowAPI extracts the client key from it.
"""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],   # global default — generous for normal use
    storage_uri=os.getenv("RATE_LIMIT_STORAGE", "memory://"),
)
