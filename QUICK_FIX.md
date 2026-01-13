# ⚡ БЫСТРОЕ ИСПРАВЛЕНИЕ - 5 МИНУТ

## 🎯 ТРИ ПРОСТЫХ ШАГА

### ШАГ 1: Автоматическая очистка (30 сек)
```powershell
.\cleanup-script.ps1 -Force
```

### ШАГ 2: Автоматическое исправление (3-5 мин)
```powershell
.\fix-and-test.ps1
```

### ШАГ 3: Запуск
```powershell
# Применить миграции БД
cd backend
.\venv\Scripts\activate
alembic upgrade head
python create_admin.py

# Запустить все сервисы
cd ..
.\start-all.bat
```

## ✅ ГОТОВО!

Откройте: **http://localhost:5173**

**Логин:** admin@medtest.local  
**Пароль:** admin123

---

## 📋 ЧТО ДЕЛАЮТ СКРИПТЫ

### cleanup-script.ps1
- ❌ Удаляет backend/venv с Python 3.7
- ❌ Удаляет node_modules_backup (~800 MB)
- ❌ Удаляет node_modules_old
- 🧹 Очищает __pycache__

### fix-and-test.ps1
- ✅ Создает новый backend/venv с Python 3.11
- ✅ Устанавливает все зависимости
- ✅ Создает .env файлы из шаблонов
- ✅ Проверяет работу сервисов
- ✅ Запускает базовые тесты

---

## 🔧 РУЧНОЕ ИСПРАВЛЕНИЕ (если нужно)

### Если скрипты не работают:

```powershell
# 1. Удалить старое окружение
Remove-Item -Recurse -Force backend\venv
Remove-Item -Recurse -Force frontend\node_modules_backup
Remove-Item -Recurse -Force frontend\node_modules_old

# 2. Создать новое backend окружение
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Создать backend/.env (используйте шаблон из DIAGNOSTIC_REPORT.md)
# 4. Создать frontend/.env:
#    VITE_API_URL=http://localhost:8000

# 5. Применить миграции
alembic upgrade head
python create_admin.py

# 6. Запустить
cd ..
.\start-all.bat
```

---

## ⚠️ ВАЖНО ПЕРЕД ЗАПУСКОМ

Убедитесь что запущены:
- ✅ PostgreSQL (порт 5432)
- ✅ Redis/Memurai (порт 6379)
- ✅ MinIO (порт 9000/9001)

Проверить можно в PowerShell:
```powershell
Test-NetConnection localhost -Port 5432
Test-NetConnection localhost -Port 6379
Test-NetConnection localhost -Port 9000
```

---

## 📖 ПОЛНАЯ ДОКУМЕНТАЦИЯ

- 📄 **DIAGNOSTIC_REPORT.md** - Полный отчет о проблемах
- 📄 **INSTALL_WINDOWS.md** - Подробная установка
- 📄 **README.md** - Общая информация о проекте

---

## 🆘 ПРОБЛЕМЫ?

### "Python не найден"
```powershell
python --version  # Должно показать 3.11+
```
Установите Python 3.11: https://www.python.org/downloads/

### "PostgreSQL не отвечает"
```powershell
Get-Service postgresql-x64-16
Start-Service postgresql-x64-16
```

### "Redis не отвечает"
```powershell
# Для Memurai:
Get-Service Memurai
Start-Service Memurai

# Для Redis:
& "C:\Program Files\Redis\redis-server.exe"
```

### "MinIO не отвечает"
```powershell
C:\minio\start-minio.bat
```

---

**Всё должно заработать! 🚀**
