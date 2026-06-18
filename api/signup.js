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

    // Read existing list
    let current = []
    try {
      console.log('[signup] calling list()')
      const { blobs } = await list({ prefix: KEY })
      console.log('[signup] list() returned', blobs.length, 'blobs')
      const hit = blobs.find(b => b.pathname === KEY)
      if (hit) {
        const blobRes = await fetch(hit.downloadUrl, {
          headers: { Authorization: `Bearer ${process.env.BLOB_READ_WRITE_TOKEN}` },
        })
        console.log('[signup] fetch existing blob status:', blobRes.status)
        if (blobRes.ok) {
          const parsed = await blobRes.json()
          if (Array.isArray(parsed)) current = parsed
        }
      }
    } catch (listErr) {
      console.log('[signup] list/read error:', String(listErr?.message || listErr))
    }

    if (!current.some(e => e.email === email)) {
      current.push({ email, ts: new Date().toISOString() })
    }

    console.log('[signup] calling put(), count:', current.length)
    await put(KEY, JSON.stringify(current, null, 2), {
      access: 'private',
      contentType: 'application/json',
      addRandomSuffix: false,
      allowOverwrite: true,
    })

    console.log('[signup] put() succeeded')
    return res.status(200).json({ ok: true, stored: true, count: current.length })
  } catch (err) {
    console.log('[signup] fatal error:', String(err?.message || err))
    return res.status(500).json({ ok: false, error: 'Storage failed', detail: String(err?.message || err) })
  }
}
