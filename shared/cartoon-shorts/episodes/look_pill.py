"""Look reel: the pill look's people and props on a plain backdrop, no story (built by showcase.reel)."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from showcase import reel  # noqa: E402

globals().update(reel('pill'))
