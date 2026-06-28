// Persistent qualitative memory buffer — the localStorage key the
// MicroInterrogation writes into when the user types a free-text reason.

export interface MemoryEntry {
  at: string
  cand: string
  kind: string
  note: string
}

const KEY = 'matrix.memoryBuffer'

export function loadMemory(): MemoryEntry[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(KEY)
    if (!raw) return []
    return JSON.parse(raw) as MemoryEntry[]
  } catch {
    return []
  }
}

export function clearMemory(): void {
  if (typeof window === 'undefined') return
  try { window.localStorage.removeItem(KEY) } catch { /* ignore */ }
}
