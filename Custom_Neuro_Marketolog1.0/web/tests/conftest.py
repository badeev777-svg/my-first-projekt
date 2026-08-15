import os
import sys
from pathlib import Path

os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault("ADMIN_LOGIN", "test")
os.environ.setdefault("ADMIN_PASSWORD", "test")

sys.path.insert(0, str(Path(__file__).parent.parent))
