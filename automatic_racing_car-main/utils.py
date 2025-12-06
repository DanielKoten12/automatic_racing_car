# utils.py
"""Utility functions untuk racing game"""

def clamp(x, a, b):
    """Membatasi nilai x antara a dan b"""
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    """Linear interpolation antara a dan b dengan faktor t"""
    return a + (b - a) * t
