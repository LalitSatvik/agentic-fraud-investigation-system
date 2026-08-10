import type { AuditLogEntry, Investigation, TransactionDetail } from "./types"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${init?.method ?? "GET"} ${path} -> ${res.status}: ${body.slice(0, 300)}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  listFlagged: () => request<Investigation[]>("/investigations/flagged"),

  getInvestigation: (id: number) => request<Investigation>(`/investigations/${id}`),

  getAuditLog: (id: number) => request<AuditLogEntry[]>(`/investigations/${id}/audit-log`),

  getTransaction: (transactionId: string) =>
    request<TransactionDetail>(`/internal/transactions/${transactionId}`),

  runInvestigation: (transactionId: string) =>
    request<Investigation>(`/investigations/${transactionId}/run`, { method: "POST" }),

  submitDecision: (
    investigationId: number,
    body: { decision: string; reviewer: string; notes?: string }
  ) =>
    request<Investigation>(`/investigations/${investigationId}/decision`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
}
