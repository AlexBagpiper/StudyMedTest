#!/usr/bin/env python3
"""
Создаёт backend/venv и ставит зависимости для разработки и тестов (requirements-dev.txt).
На сервере используйте только requirements.txt; dev-зависимости там конфликтуют.
Запуск из корня проекта: python scripts/setup_dev_venv.py
"""
import os
import subprocess
import sys

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    root = get_project_root()
    backend = os.path.join(root, "backend")
    venv_dir = os.path.join(backend, "venv")
    req_dev = os.path.join(backend, "requirements-dev.txt")

    if not os.path.exists(req_dev):
        print(f"[!] Not found: {req_dev}")
        sys.exit(1)

    if not os.path.exists(venv_dir):
        print("[*] Creating backend/venv...")
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True, cwd=root)
    else:
        print("[*] backend/venv already exists")

    if sys.platform == "win32":
        pip = os.path.join(venv_dir, "Scripts", "pip.exe")
        python = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        pip = os.path.join(venv_dir, "bin", "pip")
        python = os.path.join(venv_dir, "bin", "python")

    print("[*] Installing from requirements-dev.txt (includes requirements.txt)...")
    subprocess.run([pip, "install", "-r", req_dev], check=True, cwd=backend)
    # safety требует pydantic>=2.6, у нас 2.5.3 — снимаем, чтобы не было конфликта
    subprocess.run([pip, "uninstall", "-y", "safety", "safety-schemas"], cwd=backend, capture_output=True)
    print(f"[+] Done. Use for tests: {python} -m pytest (from backend/) or python scripts/run_tests.py")
    return 0

if __name__ == "__main__":
    sys.exit(main())
