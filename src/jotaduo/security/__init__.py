# -*- coding: utf-8 -*-
"""
Security framework for JotaDuo.

This package centralises all security-related mechanisms:

* **Tool-call guarding** (``jotaduo.security.tool_guard``)
  Pre-execution parameter scanning to detect dangerous tool usage
  patterns (command injection, data exfiltration, etc.).
* **Skill scanning** (``jotaduo.security.skill_scanner``)
  Static analysis of skill directories before install / activation.
* **Secret storage** (``jotaduo.security.secret_store``)
  Transparent encryption layer for sensitive fields (API keys, tokens)
  stored on disk.  Uses Fernet (AES-128-CBC + HMAC-SHA256) with a
  master key backed by the OS keychain or a fallback file.

Sub-modules are kept independent so each concern can evolve (or be
disabled) without affecting the others.  Import-time cost is near-zero
because heavy dependencies are lazily loaded inside each sub-module.
"""
