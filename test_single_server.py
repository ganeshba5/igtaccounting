#!/usr/bin/env python3
"""Test script to verify single-server mode setup."""

import os
import sys

# Set environment variables before importing app
os.environ['BUILD_FRONTEND'] = '1'
os.environ['FLASK_ENV'] = 'production'

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app import app, SERVE_STATIC, FRONTEND_BUILD_DIR

print("=" * 60)
print("Single-Server Mode Test")
print("=" * 60)
print(f"SERVE_STATIC: {SERVE_STATIC}")
print(f"FRONTEND_BUILD_DIR: {FRONTEND_BUILD_DIR}")
print(f"FRONTEND_BUILD_DIR exists: {os.path.exists(FRONTEND_BUILD_DIR)}")
print()
print("Registered routes (non-API):")
for rule in app.url_map.iter_rules():
    if not rule.rule.startswith('/api'):
        print(f"  {rule.rule} -> {rule.endpoint}")
print("=" * 60)

