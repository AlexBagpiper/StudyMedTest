/**
 * E2E registration flow.
 *
 * Requires:
 *   - backend up with ENVIRONMENT=development (so the OTP code is logged),
 *     OR a running MailHog (set MAILHOG_API=http://host:8025/api/v2)
 *   - frontend dev/preview server on E2E_BASE_URL
 *
 * Retrieves the OTP either via MailHog JSON API or a backend dev-only endpoint
 * (not included here — add /dev/last-otp?email=... behind ENVIRONMENT check if
 * MailHog is not available in your setup).
 */

import { expect, test } from '@playwright/test'

const MAILHOG = process.env.MAILHOG_API // e.g. http://localhost:8025/api/v2

async function fetchLatestOtp(email: string): Promise<string> {
  if (!MAILHOG) {
    throw new Error('MAILHOG_API env var is required for E2E tests')
  }
  const res = await fetch(`${MAILHOG}/search?kind=to&query=${encodeURIComponent(email)}`)
  const json: any = await res.json()
  const item = json.items?.[0]
  if (!item) throw new Error(`No email for ${email}`)
  const body: string = item.Content.Body
  const match = body.match(/\b(\d{6})\b/)
  if (!match) throw new Error('6-digit code not found in email body')
  return match[1]
}

const unique = () => `student_${Date.now()}@example.com`

test.describe('Registration flow', () => {
  test('happy path: register → verify → logged in', async ({ page }) => {
    const email = unique()
    await page.goto('/register')
    await page.getByLabel(/Фамилия/i).fill('Иванов')
    await page.getByLabel(/Имя/i).first().fill('Иван')
    await page.getByLabel(/Email/i).fill(email)
    await page.getByLabel(/^Пароль$/i).fill('Secret123')
    await page.getByLabel(/Подтвердите пароль/i).fill('Secret123')
    await page.getByRole('button', { name: /Зарегистрироваться/i }).click()

    await expect(page).toHaveURL(/\/verify-email/)

    const code = await fetchLatestOtp(email)
    await page.getByLabel(/Код подтверждения/i).fill(code)
    await page.getByRole('button', { name: /Подтвердить/i }).click()

    // After auto-login we should be on the dashboard.
    await expect(page).toHaveURL('/', { timeout: 10_000 })
  })

  test('recovers pendingEmail from localStorage after F5', async ({ page }) => {
    const email = unique()
    await page.goto('/register')
    await page.getByLabel(/Фамилия/i).fill('Иванов')
    await page.getByLabel(/Имя/i).first().fill('Иван')
    await page.getByLabel(/Email/i).fill(email)
    await page.getByLabel(/^Пароль$/i).fill('Secret123')
    await page.getByLabel(/Подтвердите пароль/i).fill('Secret123')
    await page.getByRole('button', { name: /Зарегистрироваться/i }).click()
    await expect(page).toHaveURL(/\/verify-email/)

    await page.reload()
    await expect(page.getByText(email)).toBeVisible()
  })

  test('wrong code shows Snackbar with attempts left', async ({ page }) => {
    const email = unique()
    await page.goto('/register')
    await page.getByLabel(/Фамилия/i).fill('Иванов')
    await page.getByLabel(/Имя/i).first().fill('Иван')
    await page.getByLabel(/Email/i).fill(email)
    await page.getByLabel(/^Пароль$/i).fill('Secret123')
    await page.getByLabel(/Подтвердите пароль/i).fill('Secret123')
    await page.getByRole('button', { name: /Зарегистрироваться/i }).click()
    await expect(page).toHaveURL(/\/verify-email/)

    await page.getByLabel(/Код подтверждения/i).fill('000000')
    await page.getByRole('button', { name: /Подтвердить/i }).click()
    await expect(page.getByText(/attempts left|попыт/i)).toBeVisible()
  })

  test('resend is disabled during cooldown', async ({ page }) => {
    const email = unique()
    await page.goto('/register')
    await page.getByLabel(/Фамилия/i).fill('Иванов')
    await page.getByLabel(/Имя/i).first().fill('Иван')
    await page.getByLabel(/Email/i).fill(email)
    await page.getByLabel(/^Пароль$/i).fill('Secret123')
    await page.getByLabel(/Подтвердите пароль/i).fill('Secret123')
    await page.getByRole('button', { name: /Зарегистрироваться/i }).click()
    await expect(page).toHaveURL(/\/verify-email/)

    const resendBtn = page.getByRole('button', { name: /Повторно|Отправить код повторно/ })
    await resendBtn.click()
    await expect(page.getByText(/Повторно через/)).toBeVisible()
  })

  test('LoginPage shows "continue pending registration" banner', async ({ page }) => {
    await page.evaluate(() => localStorage.setItem('pendingEmail', 'dangling@example.com'))
    await page.goto('/login')
    await expect(page.getByText(/Незавершённая регистрация/)).toBeVisible()
    await expect(page.getByText('dangling@example.com')).toBeVisible()
  })
})
