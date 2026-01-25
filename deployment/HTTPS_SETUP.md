# Настройка HTTPS

## Автоматическая настройка (рекомендуется)

### Предварительные требования
1. У вас есть домен (например, `medtest.example.com`)
2. DNS записи настроены и указывают на IP вашего сервера
3. Порты 80 и 443 открыты в файерволе

### Шаги

1. **Подготовка:**
   ```bash
   cd ~/StudyMedTest/deployment
   chmod +x scripts/init_ssl.sh
   ```

2. **Запуск скрипта:**
   ```bash
   ./scripts/init_ssl.sh medtest.example.com your-email@example.com
   ```
   
   Замените:
   - `medtest.example.com` на ваш реальный домен
   - `your-email@example.com` на ваш email (для уведомлений Let's Encrypt)

3. **Что делает скрипт:**
   - Останавливает nginx
   - Запускает certbot для получения сертификата
   - Копирует сертификаты в нужную директорию
   - Обновляет `server_name` в nginx.conf
   - Перезапускает nginx с HTTPS

4. **Готово!** Сайт доступен на `https://ваш-домен.com`

## Ручная настройка

### 1. Получение SSL сертификата

**Вариант A: Let's Encrypt (бесплатно)**

```bash
cd ~/StudyMedTest/deployment

# Создайте директории
mkdir -p certbot/www nginx/certs

# Временно запустите nginx только на порту 80
docker compose up -d nginx

# Получите сертификат
docker run -it --rm \
    -v "$(pwd)/nginx/certs:/etc/letsencrypt" \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    --network deployment_medtest-network \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email your-email@example.com \
    --agree-tos \
    --no-eff-email \
    -d your-domain.com

# Скопируйте сертификаты
cp nginx/certs/live/your-domain.com/fullchain.pem nginx/certs/fullchain.pem
cp nginx/certs/live/your-domain.com/privkey.pem nginx/certs/privkey.pem
```

**Вариант B: Свой сертификат**

Скопируйте ваши файлы сертификатов:
```bash
cp your-fullchain.pem deployment/nginx/certs/fullchain.pem
cp your-privkey.pem deployment/nginx/certs/privkey.pem
chmod 644 deployment/nginx/certs/fullchain.pem
chmod 600 deployment/nginx/certs/privkey.pem
```

### 2. Обновите nginx.conf

Откройте `deployment/nginx/nginx.conf` и замените `server_name _;` на ваш домен:

```nginx
server_name medtest.example.com;
```

### 3. Перезапустите nginx

```bash
cd deployment
docker compose restart nginx
```

## Продление сертификата

SSL сертификаты Let's Encrypt действительны 90 дней. Для продления:

```bash
cd ~/StudyMedTest/deployment

# Продлить сертификат
docker run --rm \
    -v "$(pwd)/nginx/certs:/etc/letsencrypt" \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    certbot/certbot renew

# Скопировать обновленные сертификаты
cp nginx/certs/live/your-domain.com/fullchain.pem nginx/certs/fullchain.pem
cp nginx/certs/live/your-domain.com/privkey.pem nginx/certs/privkey.pem

# Перезапустить nginx
docker compose restart nginx
```

### Автоматическое продление (cron)

Добавьте в crontab (запуск каждый понедельник в 3 утра):

```bash
crontab -e
```

Добавьте строку:
```
0 3 * * 1 cd /root/StudyMedTest/deployment && docker run --rm -v "$(pwd)/nginx/certs:/etc/letsencrypt" certbot/certbot renew && cp nginx/certs/live/YOUR-DOMAIN/fullchain.pem nginx/certs/fullchain.pem && cp nginx/certs/live/YOUR-DOMAIN/privkey.pem nginx/certs/privkey.pem && docker compose restart nginx
```

## Проверка HTTPS

После настройки проверьте:

1. **Доступность сайта:**
   ```bash
   curl -I https://your-domain.com
   ```

2. **Редирект с HTTP:**
   ```bash
   curl -I http://your-domain.com
   # Должен вернуть 301 Moved Permanently
   ```

3. **Качество SSL:**
   - Откройте https://www.ssllabs.com/ssltest/
   - Введите ваш домен
   - Вы должны получить рейтинг A или A+

## Troubleshooting

### Ошибка: "Connection refused" на 443 порту

**Решение:**
```bash
# Проверьте, что nginx слушает на 443
docker exec medtest-nginx netstat -tlnp | grep 443

# Проверьте файерволл
sudo ufw status
sudo ufw allow 443/tcp
```

### Ошибка: "SSL certificate problem"

**Решение:**
```bash
# Проверьте наличие сертификатов
ls -la deployment/nginx/certs/

# Проверьте права доступа
chmod 644 deployment/nginx/certs/fullchain.pem
chmod 600 deployment/nginx/certs/privkey.pem
```

### Ошибка: Let's Encrypt rate limit

**Причина:** Слишком много попыток получения сертификата

**Решение:**
- Подождите 1 час
- Используйте staging сервер для тестов: добавьте `--staging` к команде certbot
- После успешного теста запросите настоящий сертификат

## Тестирование без домена

Если у вас пока нет домена, можно создать self-signed сертификат для тестов:

```bash
cd deployment/nginx/certs

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout privkey.pem \
    -out fullchain.pem \
    -subj "/C=RU/ST=Moscow/L=Moscow/O=MedTest/CN=localhost"

chmod 644 fullchain.pem
chmod 600 privkey.pem
```

**Внимание:** Браузер будет предупреждать о небезопасном соединении. Это нормально для self-signed сертификатов.
