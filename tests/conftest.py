"""
Configuração global de testes.

Aqui garantimos que o diretório raiz do projeto entre no sys.path,
permitindo imports como `import src.api.main` e `import feature_repo`.
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

