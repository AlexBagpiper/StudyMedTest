# Frontend E2E tests (Playwright)

Playwright-тесты для критичных пользовательских сценариев. Запуск требует
поднятый backend и frontend (или docker-compose), плюс MailHog (или Mox) для
перехвата исходящих писем.

## Установка

```bash
cd frontend
npm install -D @playwright/test
npx playwright install --with-deps chromium
```

## Конфигурация

`playwright.config.ts`:

```ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5173',
    trace: 'on-first-retry',
  },
})
```

## Структура

- `registration.spec.ts` — полный happy path + восстановление после F5 + lockout.

## Запуск

```bash
E2E_BASE_URL=http://localhost:5173 \
MAILHOG_API=http://localhost:8025/api/v2 \
npx playwright test
```
