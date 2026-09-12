# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Byte-to-text decoding for iCalendar input with a legacy-encoding fallback.

iCalendar files from older clients (Lotus Notes, pre-Unicode Outlook) are
often saved as Windows-1252 or Latin-1 with no declared charset. This
module decodes such input without raising, since Latin-1 can decode any
byte sequence, while still preferring UTF-8 when it applies.

Windows-1252 is tried before Latin-1: it's a superset of Latin-1's
printable range and what Lotus Notes/pre-Unicode Outlook actually
produced for Western European users, and it only rejects 5 of its 128
high byte values, so there's nothing meaningful to disambiguate with
statistical detection here. An earlier version of this module used
`charset-normalizer` to choose between candidate encodings, but that
detection was measurably slower (2-10x, depending on input) than a
direct decode attempt for no accuracy benefit: every fixture tested
produced identical output either way, since a wrong guess between
cp1252 and Latin-1 on this narrow candidate set is not something
detection could improve on. That dependency was removed as a result.

Non-Western-European text encoded in a different legacy code page (for
example Polish in cp1250, Turkish in cp1254) will decode without
raising but can produce plausible-looking, silently wrong characters,
since cp1252 has a defined mapping for nearly every byte value. There
is no reliable way to detect this case from short calendar-property
text alone; this is a known, accepted limitation.
"""

import logging
from email.message import Message

logger = logging.getLogger(__name__)


def decode_ics_bytes(data: bytes | bytearray, encoding: str | None = None) -> tuple[str, str]:
    """Decode raw iCalendar bytes to text, tolerating legacy encodings.

    Tries, in order: an explicit override, UTF-8, Windows-1252, then
    Latin-1 (which cannot fail to decode any byte sequence).

    Args:
        data: Raw bytes read from a file, upload, or HTTP response.
        encoding: Optional explicit encoding to force. Bypasses the
            UTF-8/cp1252/Latin-1 chain.

    Returns:
        A ``(text, encoding_used)`` tuple. ``encoding_used`` is the codec
        name that was applied: the caller-supplied override, ``"utf-8"``,
        ``"cp1252"``, or ``"latin-1"``.

    Raises:
        UnicodeDecodeError: If `encoding` is given but decoding with it
            fails. Never raised when `encoding` is None, because the
            Latin-1 fallback always succeeds.
        LookupError: If `encoding` names an unknown codec.
    """
    if encoding is not None:
        return data.decode(encoding), encoding

    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass

    try:
        text = data.decode("cp1252")
    except UnicodeDecodeError:
        # INFO, not WARNING: this path is reachable from arbitrary
        # remote input (uploaded files, fetched URLs), so unusual-but-
        # harmless bytes would otherwise flood production logs.
        logger.info("Could not decode as cp1252; falling back to Latin-1")
        return data.decode("latin-1"), "latin-1"
    else:
        logger.info("Decoded as cp1252")
        return text, "cp1252"


def charset_from_content_type(content_type: str | None) -> str | None:
    """Extract a ``charset`` parameter from a Content-Type header value.

    Uses `email.message.Message`'s RFC 2045 parameter parsing (quoted
    values, case-insensitive parameter names) rather than hand-rolling a
    parser for a header format with more edge cases than it looks like.
    Callers that already have a parsed charset from their own HTTP
    library (for example `httpx.Response.charset_encoding`) should use
    that directly instead of re-parsing the raw header through this.

    Args:
        content_type: A raw ``Content-Type`` header value, or `None`.

    Returns:
        The declared charset name, or `None` if absent.
    """
    if content_type is None:
        return None
    message = Message()
    message["content-type"] = content_type
    return message.get_content_charset()


def decode_ics_bytes_with_declared_charset(
    data: bytes | bytearray, declared_charset: str | None
) -> tuple[str, str]:
    """Decode bytes, preferring a caller-declared charset over auto-detection.

    A source that explicitly states its own charset (an HTTP response's
    ``Content-Type`` header, a multipart upload part's declared type) is
    authoritative when accurate, so it's tried first. Sources lie about
    their own encoding often enough in practice that a decode failure
    there still falls through to `decode_ics_bytes`'s normal detection
    chain rather than raising.

    Args:
        data: Raw bytes to decode.
        declared_charset: A charset name the source claims to use (see
            `charset_from_content_type` to extract one from a raw
            Content-Type header), or `None` if none was declared.

    Returns:
        A ``(text, encoding_used)`` tuple, same shape as `decode_ics_bytes`.
    """
    if declared_charset is not None:
        try:
            return data.decode(declared_charset), declared_charset
        except (UnicodeDecodeError, LookupError):
            pass
    return decode_ics_bytes(data)


def decode_ics_bytes_with_content_type(data: bytes | bytearray, content_type: str | None) -> str:
    """Decode bytes, preferring a charset declared in a raw Content-Type header.

    Combines `charset_from_content_type` and
    `decode_ics_bytes_with_declared_charset` for the common case of a
    caller that only has the raw header string (a multipart upload
    part's declared type, a request's ``Content-Type`` header) and
    doesn't need to know which encoding was ultimately used.

    Args:
        data: Raw bytes to decode.
        content_type: A raw ``Content-Type`` header value, or `None`.

    Returns:
        The decoded text.
    """
    declared_charset = charset_from_content_type(content_type)
    text, _encoding_used = decode_ics_bytes_with_declared_charset(data, declared_charset)
    return text
