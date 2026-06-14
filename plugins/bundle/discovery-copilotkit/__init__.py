# -*- coding: utf-8 -*-
"""Discovery + CopilotKit plugin package.

Intentionally empty so the directory works under both load paths the
platform supports:

1. ``qwenpaw.plugins.loader`` loads ``plugin.py`` via
   ``importlib.util.spec_from_file_location`` with
   ``submodule_search_locations``; the modules ``plugin.py`` imports use
   the sys.path trick (see ``plugin.py``).
2. Tests / eval add the plugin dir to ``sys.path`` and import siblings
   directly (``import router``, ``from copilotkit_adapter import ...``).

Keeping this file empty side-steps the hyphen-in-folder problem (this
directory is *not* a regular Python package).
"""
