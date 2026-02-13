import os
import subprocess
import sys
import asyncio

# Добавляем путь к бэкенду, чтобы импортировать llm_service
sys.path.append(os.path.join(os.getcwd(), 'backend'))

async def generate_smart_test(filepath):
    """Генерация осмысленного теста через LLMService."""
    if not filepath.endswith(('.py', '.ts', '.tsx')):
        return
    
    # Определение пути для сохранения теста
    test_path = ""
    if filepath.startswith('backend/app/api') or filepath.startswith('backend/app/services'):
        test_path = filepath.replace('backend/app', 'backend/tests').replace('.py', '_test.py')
    elif filepath.startswith('frontend/src'):
        # Для фронтенда кладем в __tests__ рядом с файлом или в общую папку
        dir_name = os.path.dirname(filepath)
        base_name = os.path.basename(filepath)
        test_dir = os.path.join(dir_name, '__tests__')
        if not os.path.exists(test_dir):
            os.makedirs(test_dir, exist_ok=True)
        test_path = os.path.join(test_dir, base_name.replace('.tsx', '.test.tsx').replace('.ts', '.test.ts'))
    
    if not test_path or os.path.exists(test_path):
        return

    print(f"[*] Generating smart test for {filepath}...")
    
    try:
        from app.services.llm_service import llm_service
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Вызов LLM для генерации кода
        generated_code = await llm_service.generate_test_code(content, filepath)
    except ImportError as e:
        print(f"[!] Skipping smart generation for {filepath}: Missing dependency ({e}). Run 'pip install -r backend/requirements.txt'")
        return
    except Exception as e:
        print(f"[!] Failed to generate smart test for {filepath}: {e}")
        return
        
        # Очистка от возможных markdown-тегов, если LLM их все же добавила
        if "```" in generated_code:
            import re
            match = re.search(r'```(?:python|typescript|tsx|javascript)?\s*(.*?)\s*```', generated_code, re.DOTALL)
            if match:
                generated_code = match.group(1)

        with open(test_path, 'w', encoding='utf-8') as f:
            f.write(generated_code)
            
        print(f"[+] Smart test generated at: {test_path}")
    except Exception as e:
        print(f"[!] Failed to generate smart test for {filepath}: {e}")

def get_changed_files():
    """Получение списка измененных файлов через Git."""
    try:
        # Проверяем и закоммиченные (но не пушнутые) и незакоммиченные изменения
        # stderr=subprocess.DEVNULL подавляет варнинги о переносе строк (LF -> CRLF)
        output = subprocess.check_output(
            ["git", "diff", "--name-only", "HEAD"], 
            text=True, 
            stderr=subprocess.DEVNULL
        )
        return list(set(output.splitlines()))
    except Exception:
        return []

async def main():
    changed_files = get_changed_files()
    if not changed_files:
        print("[*] No changes detected. Skipping auto-generation.")
        return

    tasks = [generate_smart_test(f) for f in changed_files]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    # Убедимся, что PYTHONPATH включает backend для корректного импорта app
    os.environ['PYTHONPATH'] = os.path.join(os.getcwd(), 'backend')
    asyncio.run(main())
