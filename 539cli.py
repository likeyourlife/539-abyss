"""539核心包CLI入口"""

import sys
import os

# 确保项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from importlib import import_module
cli = import_module('539_core.cli')
cli.main()
