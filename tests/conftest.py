"""
Configuração global de testes.

Aqui garantimos que o diretório raiz do projeto entre no sys.path,
permitindo imports como `import src.api.main` e `import feature_repo`.
"""

import sys
from pathlib import Path

# Fix for Feast/Gunicorn imports on Windows
if sys.platform == "win32":
    import types
    # Mock fcntl
    fcntl_mock = types.ModuleType("fcntl")
    fcntl_mock.fcntl = lambda fd, cmd, arg=0: 0
    fcntl_mock.ioctl = lambda fd, cmd, arg=0: arg
    fcntl_mock.F_SETFL = 0
    fcntl_mock.F_GETFL = 0
    sys.modules["fcntl"] = fcntl_mock

    # Mock termios
    termios_mock = types.ModuleType("termios")
    termios_mock.TIOCGWINSZ = 0
    sys.modules["termios"] = termios_mock

    # Mock pwd
    pwd_mock = types.ModuleType("pwd")
    pwd_mock.getpwuid = lambda uid: None
    sys.modules["pwd"] = pwd_mock

    # Mock gunicorn completely to avoid AF_UNIX and other POSIX-only stuff
    class MockGunicornAppBase:
        class BaseApplication:
            pass

    class MockGunicornApp:
        pass

    class MockGunicorn:
        pass

    mock_gunicorn = types.ModuleType("gunicorn")
    mock_gunicorn_app = types.ModuleType("gunicorn.app")
    mock_gunicorn_app_base = types.ModuleType("gunicorn.app.base")

    mock_gunicorn_app_base.BaseApplication = MockGunicornAppBase.BaseApplication
    mock_gunicorn_app.base = mock_gunicorn_app_base
    mock_gunicorn.app = mock_gunicorn_app

    sys.modules["gunicorn"] = mock_gunicorn
    sys.modules["gunicorn.app"] = mock_gunicorn_app
    sys.modules["gunicorn.app.base"] = mock_gunicorn_app_base

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

