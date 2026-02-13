import os
import subprocess
import sys

def get_python_executable():
    """Находит путь к python в виртуальном окружении."""
    # Проверяем backend/venv/Scripts/python.exe (Windows)
    venv_python = os.path.join(os.getcwd(), "backend", "venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        return venv_python
    
    # Проверяем backend/venv/bin/python (Linux/macOS)
    venv_python_unix = os.path.join(os.getcwd(), "backend", "venv", "bin", "python")
    if os.path.exists(venv_python_unix):
        return venv_python_unix
        
    return sys.executable

def main():
    python_exe = get_python_executable()
    print(f"[*] Using python: {python_exe}")
    
    # 1. Запуск автогенерации тестов
    print("\n[*] Step 1: Auto-generating tests...")
    auto_test_cmd = [python_exe, "scripts/auto_test.py"]
    subprocess.run(auto_test_cmd)
    
    # 2. Запуск всех тестов
    print("\n[*] Step 2: Running tests...")
    run_tests_cmd = [python_exe, "scripts/run_tests.py"]
    result = subprocess.run(run_tests_cmd)
    
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
