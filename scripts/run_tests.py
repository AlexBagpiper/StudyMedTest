#!/usr/bin/env python3
import os
import subprocess
import sys

def get_python_executable():
    """Returns the path to the python executable in the venv if it exists, else sys.executable."""
    venv_python = os.path.join(os.getcwd(), "backend", "venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable

def run_backend_tests():
    print("\n--- Running Backend Tests ---")
    os.chdir("backend")
    python_exe = get_python_executable()
    # Using the detected python to run pytest
    result = subprocess.run([python_exe, "-m", "pytest"], shell=True)
    os.chdir("..")
    return result.returncode

def run_frontend_tests():
    print("\n--- Running Frontend Tests ---")
    os.chdir("frontend")
    # Using vitest
    result = subprocess.run(["npm", "test", "--", "--run"], shell=True)
    os.chdir("..")
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
