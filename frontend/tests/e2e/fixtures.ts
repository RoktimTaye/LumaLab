import { test as base, expect } from '@playwright/test'

export const test = base.extend<{ resetImageStore: void }>({
  resetImageStore: [async ({ request }, use) => {
    const response = await request.post(`${process.env.LUMALAB_TEST_API ?? 'http://127.0.0.1:8000'}/__test/reset`)
    expect(response.status(), 'Start backend/scripts/e2e_server.py for isolated browser tests').toBe(204)
    await use()
  }, { auto: true }],
})

export { expect }
