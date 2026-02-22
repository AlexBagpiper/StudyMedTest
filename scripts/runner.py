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
    
    # 2. Проверка безопасности (Security Checks)
    print("\n[*] Step 2: Running security checks...")
    
    # Bandit (Backend code)
    print("[*] Running Bandit (Backend code security)...")
    subprocess.run([python_exe, "-m", "bandit", "-r", "backend", "-x", "backend/tests,backend/venv"], check=False)
    
    # Safety (Backend dependencies)
    print("\n[*] Running Safety (Backend dependencies security)...")
    # Используем --stdin для передачи списка установленных пакетов или просто проверяем requirements
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

    # 4. Запуск всех тестов
    print("\n[*] Step 4: Running functional tests...")
    run_tests_cmd = [python_exe, "scripts/run_tests.py"]
    result = subprocess.run(run_tests_cmd)
    
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
