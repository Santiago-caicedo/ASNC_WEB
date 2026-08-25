"""Shared anti-spam helpers for the public forms.

Kept here (and not inside an app) because both `admissions` and `website`
need them. Two strictness levels:

- validate_no_spam()   -> short fields (name, profession, subject) where a URL
                          is never legitimate.
- validate_free_text() -> message bodies, where one link may be legitimate.
"""

import re

from django.core.exceptions import ValidationError


# Disposable email domains blocklist
BLOCKED_EMAIL_DOMAINS = {
    'mailbox.in.ua', 'tempmail.com', 'guerrillamail.com', 'throwaway.email',
    'maildrop.cc', 'mailnesia.com', 'yopmail.com', 'trashmail.com',
    'fakeinbox.com', 'sharklasers.com', 'guerrillamailblock.com',
    'grr.la', 'dispostable.com', 'mailinator.com', 'temp-mail.org',
    'minutemail.com', 'tempail.com', 'mohmal.com', '10minutemail.com',
    'guerrillamail.info', 'guerrillamail.net', 'guerrillamail.de',
    'emailondeck.com', 'mailcatch.com', 'tempr.email',
}

URL_PATTERN = re.compile(
    r'(https?://|www\.|\.com|\.net|\.org|\.io|\.ru|\.ua|://)',
    re.IGNORECASE,
)
MONEY_PATTERN = re.compile(r'[\$\u20ac\u00a3]\s?\d[\d,\.]+')
SPAM_KEYWORDS = re.compile(
    r'(deposit|withdraw|crypto|bitcoin|casino|lottery|prize|click here|confirm your)',
    re.IGNORECASE,
)


def validate_no_spam(value, field_label):
    """Reject values containing URLs, money patterns, or spam keywords."""
    if not value:
        return value
    if URL_PATTERN.search(value):
        raise ValidationError(f'{field_label} contiene contenido no permitido.')
    if MONEY_PATTERN.search(value):
        raise ValidationError(f'{field_label} contiene contenido no permitido.')
    if SPAM_KEYWORDS.search(value):
        raise ValidationError(f'{field_label} contiene contenido no permitido.')
    return value


def validate_free_text(value, field_label, max_links=1):
    """Like validate_no_spam, but tolerates up to `max_links` link-like tokens.

    A legitimate message may mention one company domain; a wall of links is spam.
    """
    if not value:
        return value
    if len(URL_PATTERN.findall(value)) > max_links:
        raise ValidationError(
            f'{field_label} contiene demasiados enlaces. '
            'Si necesitas compartir varios, escríbenos directamente a info@asncol.com.'
        )
    if MONEY_PATTERN.search(value):
        raise ValidationError(f'{field_label} contiene contenido no permitido.')
    if SPAM_KEYWORDS.search(value):
        raise ValidationError(f'{field_label} contiene contenido no permitido.')
    return value


def validate_email_domain(email):
    """Reject known disposable email providers."""
    domain = email.split('@')[-1].lower()
    if domain in BLOCKED_EMAIL_DOMAINS:
        raise ValidationError(
            'Por favor usa un correo electrónico válido. No se permiten correos temporales.'
        )
    return email
