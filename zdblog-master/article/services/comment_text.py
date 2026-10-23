"""Stable normalization for keywords and whole-comment duplicate detection."""
import hashlib
import unicodedata


def normalize(content):
    return ''.join(c for c in unicodedata.normalize('NFKC', content).casefold() if c.isalnum())


def content_fingerprint(content):
    # Preserve emoji and symbols so different reactions/code are not conflated.
    normalized = unicodedata.normalize('NFKC', content).casefold()
    canonical = ''.join(
        c for c in normalized
        if not c.isspace() and unicodedata.category(c) not in ('Cf', 'Cc')
        and not unicodedata.category(c).startswith('P')
    )
    return hashlib.sha256((canonical or normalized.strip()).encode('utf-8')).hexdigest()
