"""Server-side attachment validation: size, extension allowlist, and content sniffing."""
from pathlib import Path

from django.conf import settings
from rest_framework import serializers

# Magic-byte signatures for the allowed file types.
_SIGNATURES = {
    'jpg': [b'\xff\xd8\xff'],
    'jpeg': [b'\xff\xd8\xff'],
    'png': [b'\x89PNG\r\n\x1a\n'],
    'gif': [b'GIF87a', b'GIF89a'],
    'webp': [b'RIFF'],
    'pdf': [b'%PDF-'],
    'doc': [b'\xd0\xcf\x11\xe0'],
    'docx': [b'PK\x03\x04'],
}


def validate_attachment(uploaded_file):
    """Reject files that are too large, have a disallowed extension,
    or whose content does not match the claimed extension."""
    max_bytes = settings.MAX_ATTACHMENT_SIZE_MB * 1024 * 1024
    if uploaded_file.size > max_bytes:
        raise serializers.ValidationError(
            f'File too large. Maximum size is {settings.MAX_ATTACHMENT_SIZE_MB}MB.'
        )

    extension = Path(uploaded_file.name).suffix.lstrip('.').lower()
    if extension not in settings.ALLOWED_ATTACHMENT_EXTENSIONS:
        raise serializers.ValidationError(
            f'File type ".{extension}" is not allowed. '
            f'Allowed types: {", ".join(settings.ALLOWED_ATTACHMENT_EXTENSIONS)}.'
        )

    header = uploaded_file.read(16)
    uploaded_file.seek(0)
    signatures = _SIGNATURES.get(extension, [])
    if signatures and not any(header.startswith(sig) for sig in signatures):
        raise serializers.ValidationError(
            'File content does not match its extension.'
        )

    return uploaded_file
