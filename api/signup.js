// POST /api/signup  { email }
// Appends the email to a JSON array stored in Vercel Blob. Zero external DB.
// No-ops gracefully when BLOB_READ_WRITE_TOKEN is not configured.
import { put, list } from '@vercel/blob'

export const config = { runtime: 'nodejs' }

const KEY = 'signups.json'

export default async function handler(req, res) {
  console.log('[signup] invoked', req.method, JSON.stringify(req.body))
  try {
    if (req.method !== 'POST') {
      res.setHeader('Allow', 'POST')
      return res.status(405).json({ ok: false, error: 'Method not allowed' })
    }

    const email = String(req.body?.email || '').trim().toLowerCase()
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return res.status(400).json({ ok: false, error: 'Enter a valid email' })
    }

    console.log('[signup] token present:', !!process.env.BLOB_READ_WRITE_TOKEN)
    if (!process.env.BLOB_READ_WRITE_TOKEN) {
      return res.status(200).json({ ok: true, stored: false, reason: 'blob-not-configured' })
    }

    // Read existing list (private blob requires auth header)
    let current = []
    try {
      const { blobs } = await list({ prefix: KEY })
      const hit = blobs.find(b => b.pathname === KEY)
      if (hit) {
        const blobRes = await fetch(hit.downloadUrl, {
          headers: { Authorization: `Bearer ${process.env.BLOB_READ_WRITE_TOKEN}` },
        })
        if (blobRes.ok) {
          const parsed = await blobRes.json()
          if (Array.isArray(parsed)) current = parsed
        }
      }
    } catch { /* no existing file — start fresh */ }

    if (!current.some(e => e.email === email)) {
      current.push({ email, ts: new Date().toISOString() })
    }

    await put(KEY, JSON.stringify(current, null, 2), {
      access: 'private',
      contentType: 'application/json',
      addRandomSuffix: false,
      allowOverwrite: true,
    })

    return res.status(200).json({ ok: true, stored: true, count: current.length })
  } catch (err) {
    return res.status(500).json({ ok: false, error: 'Storage failed', detail: String(err?.message || err) })
  }
}
