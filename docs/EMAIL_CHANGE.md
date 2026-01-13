# Смена Email через подтверждение кодом

## Описание

Реализована безопасная смена email пользователя через код подтверждения, отправляемый на новый email адрес.

## Архитектура

### Backend

#### Модель User (app/models/user.py)
Добавлены поля:
- `pending_email` - новый email, ожидающий подтверждения
- `email_change_code` - 6-значный код подтверждения
- `email_change_expires` - срок действия кода (15 минут)

#### API Endpoints (app/api/v1/users.py)

**1. Запрос смены email**
```
POST /api/v1/users/me/request-email-change
Content-Type: application/json

{
  "new_email": "newemail@example.com"
}
```

Ответ (в dev режиме):
```json
{
  "message": "Confirmation code sent to new email",
  "email": "newemail@example.com",
  "dev_code": "123456"  // только в development
}
```

**2. Подтверждение смены email**
```
POST /api/v1/users/me/confirm-email-change
Content-Type: application/json

{
  "code": "123456"
}
```

Ответ:
```json
{
  "message": "Email changed successfully",
  "old_email": "oldemail@example.com",
  "new_email": "newemail@example.com"
}
```

**3. Отмена смены email**
```
DELETE /api/v1/users/me/cancel-email-change
```

Ответ:
```json
{
  "message": "Email change request cancelled"
}
```

#### Email Service (app/services/email_service.py)
Функция `send_email_change_code()` отправляет красивое HTML письмо с кодом подтверждения.

### Frontend

#### ProfilePage.tsx
Добавлен UI для смены email:
- Кнопка "Изменить email" в профиле
- Модальное окно с двумя шагами:
  1. Ввод нового email → отправка кода
  2. Ввод кода подтверждения → смена email

## Безопасность

### Защита от прямой смены
- В схеме `UserUpdate` нет поля `email` - прямая смена через PUT /users/me невозможна
- Email можно сменить ТОЛЬКО через подтверждение кодом

### Валидации
1. Проверка что новый email не занят другим пользователем
2. Проверка срока действия кода (15 минут)
3. Проверка корректности 6-значного кода
4. Race condition protection - повторная проверка занятости email перед сменой

### Генерация кода
Используется криптографически стойкий генератор `secrets.randbelow()` для создания 6-значного кода.

## Миграции

Миграция: `20260113_1600_email_change_fields.py`

Для применения:
```bash
cd backend
alembic upgrade head
```

## Использование

### Для пользователя

1. Открыть профиль
2. Нажать "Изменить email"
3. Ввести новый email
4. Получить код на новый email
5. Ввести код в форму
6. Email изменен!

### Для администратора

#### Dev режим
В режиме разработки (`ENVIRONMENT=development`):
- Email не отправляются реально
- Код выводится в консоль и возвращается в API ответе
- Удобно для тестирования без SMTP

#### Production режим
Настроить SMTP в `.env`:
```env
ENVIRONMENT=production
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@yourapp.com
```

## Локализация

Поддержка русского и английского языков:
- `profile.changeEmail` - "Изменить email" / "Change email"
- `profile.newEmail` - "Новый email" / "New email"
- `profile.enterCode` - "Введите код из письма" / "Enter code from email"
- И другие...

## Тестирование

### Вручную

1. Запустить backend:
```bash
cd backend
uvicorn app.main:app --reload
```

2. Запустить frontend:
```bash
cd frontend
npm run dev
```

3. Зайти в профиль и протестировать смену email

### API тесты
```bash
cd backend
pytest tests/test_auth.py::test_email_change -v
```

## Ограничения

- Один активный запрос на смену email
- Срок действия кода: 15 минут
- Длина кода: 6 цифр
- Нельзя сменить на уже занятый email

## Расширения

Возможные улучшения:
1. Rate limiting - ограничение частоты запросов кодов
2. История изменений email в audit log
3. Уведомление на старый email о смене
4. 2FA при смене email для дополнительной безопасности
5. Блокировка повторной смены в течение определенного периода
