# -*- coding: utf-8 -*-
"""Shared constants and enums for the ai-productions plugin."""

from __future__ import annotations

import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).parent

_plugin_dir_str = str(PLUGIN_DIR)
if _plugin_dir_str not in sys.path:
    sys.path.insert(0, _plugin_dir_str)

PLUGIN_ID = "ai-productions"

# ----------------------------------------------------------------------
# Production types
# ----------------------------------------------------------------------
# Free-form, but the UI and filters use these canonical labels.
PRODUCTION_TYPES: tuple[str, ...] = (
    "post",
    "landing_page",
    "document",
    "email",
    "ad_creative",
    "image",
    "video",
    "script",
    "blog_article",
    "social_caption",
    "press_release",
    "newsletter",
    "report",
    "spreadsheet",
    "code_snippet",
    "other",
)

PRODUCTION_TYPE_LABELS_PT: dict[str, str] = {
    "post": "Post",
    "landing_page": "Landing Page",
    "document": "Documento",
    "email": "E-mail",
    "ad_creative": "Peça de Anúncio",
    "image": "Imagem",
    "video": "Vídeo",
    "script": "Roteiro",
    "blog_article": "Artigo de Blog",
    "social_caption": "Legenda Social",
    "press_release": "Press Release",
    "newsletter": "Newsletter",
    "report": "Relatório",
    "spreadsheet": "Planilha",
    "code_snippet": "Trecho de Código",
    "other": "Outro",
}

# ----------------------------------------------------------------------
# Statuses
# ----------------------------------------------------------------------
STATUS_DRAFT = "draft"
STATUS_PENDING = "pending_approval"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_PUBLISHED = "published"
STATUS_ARCHIVED = "archived"

ALL_STATUSES: tuple[str, ...] = (
    STATUS_DRAFT,
    STATUS_PENDING,
    STATUS_APPROVED,
    STATUS_REJECTED,
    STATUS_PUBLISHED,
    STATUS_ARCHIVED,
)

# Valid transitions: which statuses can move to which.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    STATUS_DRAFT: {STATUS_PENDING, STATUS_ARCHIVED},
    STATUS_PENDING: {STATUS_APPROVED, STATUS_REJECTED, STATUS_ARCHIVED},
    STATUS_APPROVED: {STATUS_PUBLISHED, STATUS_ARCHIVED, STATUS_PENDING},
    STATUS_REJECTED: {STATUS_PENDING, STATUS_ARCHIVED},
    STATUS_PUBLISHED: {STATUS_ARCHIVED},
    STATUS_ARCHIVED: set(),
}

# ----------------------------------------------------------------------
# Notifications
# ----------------------------------------------------------------------
NOTIFICATION_LEVELS: tuple[str, ...] = ("info", "success", "warning", "error")

NOTIFICATION_KIND_PRODUCTION_NEW = "production.new"
NOTIFICATION_KIND_APPROVAL_REQUESTED = "production.approval_requested"
NOTIFICATION_KIND_APPROVED = "production.approved"
NOTIFICATION_KIND_REJECTED = "production.rejected"
NOTIFICATION_KIND_PUBLISHED = "production.published"
NOTIFICATION_KIND_CUSTOM = "team.custom"

ALL_NOTIFICATION_KINDS: tuple[str, ...] = (
    NOTIFICATION_KIND_PRODUCTION_NEW,
    NOTIFICATION_KIND_APPROVAL_REQUESTED,
    NOTIFICATION_KIND_APPROVED,
    NOTIFICATION_KIND_REJECTED,
    NOTIFICATION_KIND_PUBLISHED,
    NOTIFICATION_KIND_CUSTOM,
)

# ----------------------------------------------------------------------
# Defaults
# ----------------------------------------------------------------------
DEFAULT_TEAM = "marketing"
MAX_CONTENT_PREVIEW = 4000  # characters; longer payloads still stored
DEFAULT_REQUIRES_APPROVAL = True
