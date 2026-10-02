#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兼容转发脚本：调用 scripts/automation/auto_sync.py"""
import os, sys, subprocess

if __name__ == '__main__':
    target = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'automation', 'auto_sync.py')
    sys.exit(subprocess.call([sys.executable, target] + sys.argv[1:]))
