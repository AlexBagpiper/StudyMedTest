import os
import subprocess
import sys

def get_project_root():
    """Корень проекта (родитель каталога scripts/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_python_executable():
    """Находит python в backend/venv для dev и тестов. Иначе sys.executable."""
    root = get_project_root()
    venv_python = os.path.join(root, "backend", "venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        return venv_python
    venv_python_unix = os.path.join(root, "backend", "venv", "bin", "python")
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
    
    # 2. Проверка безопасности (Security Checks)
    print("\n[*] Step 2: Running security checks...")
    
    # Bandit (Backend code)
    print("[*] Running Bandit (Backend code security)...")
    subprocess.run([python_exe, "-m", "bandit", "-r", "backend", "-x", "backend/tests,backend/venv"], check=False)
    
    # Safety (Backend dependencies). В dev-venv не ставится (конфликт с pydantic 2.5.x).
    subprocess.run([python_exe, "-m", "safety", "check", "-r", "backend/requirements.txt"], check=False)
    
    # NPM Audit (Frontend dependencies)
    print("\n[*] Running NPM Audit (Frontend dependencies security)...")
    os.chdir("frontend")
    subprocess.run(["npm", "audit"], shell=True, check=False)
    os.chdir("..")
    
    # 3. Проверка контейнеризации (Container Checks)
    print("\n[*] Step 3: Checking container configuration...")
    # Пытаемся запустить docker-compose config для валидации
    try:
        os.chdir("deployment")
        # Проверяем наличие docker-compose в системе
        import shutil
        if shutil.which("docker-compose"):
            # Создаем пустой .env если его нет, чтобы docker-compose config не ругался
            temp_env = False
            if not os.path.exists(".env"):
                with open(".env", "w") as f:
                    f.write("POSTGRES_PASSWORD=dummy\nMINIO_ROOT_USER=dummy\nMINIO_ROOT_PASSWORD=dummy\nSECRET_KEY=dummy\n")
                temp_env = True
                
            result = subprocess.run(["docker-compose", "config", "-q"], shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print("[+] Docker Compose configuration is valid.")
            else:
                print(f"[-] Docker Compose validation failed:\n{result.stderr}")
            
            if temp_env:
                os.remove(".env")
        else:
            print("[*] Docker Compose not found on this machine. Skipping deep validation, but static checks will run in pytest.")
        os.chdir("..")
    except Exception as e:
        print(f"[!] Note: Skipping deep Docker validation: {e}")
        if os.getcwd().endswith("deployment"):
            os.chdir("..")

    # 4. Запуск всех тестов (cwd=корень, чтобы run_tests нашёл backend/venv)
    print("\n[*] Step 4: Running functional tests...")
    root = get_project_root()
    run_tests_cmd = [python_exe, "scripts/run_tests.py"]
    result = subprocess.run(run_tests_cmd, cwd=root)
    
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
