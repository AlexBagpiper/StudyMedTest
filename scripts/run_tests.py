#!/usr/bin/env python3
import os
import subprocess
import sys

def get_project_root():
    """Project root (parent of scripts/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_python_executable():
    """Returns backend/venv python if it exists, else sys.executable. Use for dev & testing."""
    root = get_project_root()
    # Windows
    venv_python = os.path.join(root, "backend", "venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        return venv_python
    # Linux/macOS
    venv_python_unix = os.path.join(root, "backend", "venv", "bin", "python")
    if os.path.exists(venv_python_unix):
        return venv_python_unix
    return sys.executable

def run_backend_tests():
    print("\n--- Running Backend Tests ---")
    root = get_project_root()
    python_exe = get_python_executable()
    if python_exe == sys.executable:
        print("[!] Backend venv not found. Run: python scripts/setup_dev_venv.py")
    backend_dir = os.path.join(root, "backend")
    result = subprocess.run([python_exe, "-m", "pytest"], shell=True, cwd=backend_dir)
    return result.returncode

def run_frontend_tests():
    print("\n--- Running Frontend Tests ---")
    root = get_project_root()
    frontend_dir = os.path.join(root, "frontend")
    result = subprocess.run(["npm", "test", "--", "--run"], shell=True, cwd=frontend_dir)
    return result.returncode

def main():
    backend_code = run_backend_tests()
    frontend_code = run_frontend_tests()
    
    if backend_code == 0 and frontend_code == 0:
        print("\n[SUCCESS] All tests passed!")
        sys.exit(0)
    else:
        print("\n[FAILURE] Some tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
