# AcousticSpace — models package
#
# Re-export Base and every ORM model so that any module that calls
# Base.metadata.create_all() after importing from here will find all
# table definitions registered on the shared metadata.
#
# Import order matters: Base must be defined (in user.py) before the
# models that reference it (analysis_history.py) are imported.

from models.user import Base, User                            # noqa: F401
from models.analysis_history import AnalysisHistory           # noqa: F401

__all__ = ["Base", "User", "AnalysisHistory"]
