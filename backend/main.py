try:
    from .presentation.api import app
except ImportError:
    from presentation.api import app
