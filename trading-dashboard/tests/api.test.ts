import { describe, expect, test, beforeEach, afterEach, vi } from "vitest"
import { z } from "zod"
import { apiGet } from "../lib/api"

const schema = z.object({ ok: z.boolean() })

describe("apiGet", () => {
  const originalFetch = global.fetch
  beforeEach(() => {
    // @ts-ignore
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ok: true }),
    })
  })
  afterEach(() => {
    global.fetch = originalFetch
  })

  test("uses proxy endpoint", async () => {
    await apiGet("/test", schema)
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/proxy?path=%2Ftest",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
        cache: "no-store",
      }),
    )
  })

  test("handles API responses correctly", async () => {
    const result = await apiGet("/test", schema)
    expect(result).toEqual({ ok: true })
  })

  test("throws error on failed requests", async () => {
    // @ts-ignore
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
    })

    await expect(apiGet("/test", schema)).rejects.toThrow("API request failed: 500 Internal Server Error")
  })
})
