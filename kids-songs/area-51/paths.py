"""Puts the sibling props on sys.path: ../hooded-man, ../../shared/lowpoly-gl and the Story Time with Kenji props."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ('../hooded-man', '../../shared/lowpoly-gl', '../storytime-kit', '../storytime-music', '../storytime-narrator'):
    q = os.path.normpath(os.path.join(HERE, p))
    if q not in sys.path:
        sys.path.insert(0, q)
