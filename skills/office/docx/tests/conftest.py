# -*- coding: utf-8 -*-
"""pytest 配置 — 把 repo 根目录加入 sys.path，使 ``skills.office.docx.*`` 可导入。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
