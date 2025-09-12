"use client"

import { useState, useCallback } from "react"
import { toast } from "sonner"

interface ErrorState {
  message: string
  code?: string
  timestamp: number
  context?: string
}

export function useErrorHandler() {
  const [errors, setErrors] = useState<ErrorState[]>([])

  const handleError = useCallback((error: unknown, context?: string) => {
    let errorMessage = "An unexpected error occurred"
    let errorCode: string | undefined

    if (error instanceof Error) {
      errorMessage = error.message
      errorCode = error.name
    } else if (typeof error === "string") {
      errorMessage = error
    } else if (error && typeof error === "object" && "message" in error) {
      errorMessage = String(error.message)
    }

    const errorState: ErrorState = {
      message: errorMessage,
      code: errorCode,
      timestamp: Date.now(),
      context,
    }

    setErrors((prev) => [errorState, ...prev.slice(0, 9)]) // Keep last 10 errors

    // Show toast notification for user-facing errors
    if (context !== "background") {
      toast.error(errorMessage, {
        description: context ? `Context: ${context}` : undefined,
      })
    }

    console.error(`[v0] Error in ${context || "unknown context"}:`, error)
  }, [])

  const clearErrors = useCallback(() => {
    setErrors([])
  }, [])

  const clearError = useCallback((timestamp: number) => {
    setErrors((prev) => prev.filter((error) => error.timestamp !== timestamp))
  }, [])

  return {
    errors,
    handleError,
    clearErrors,
    clearError,
  }
}
