// POST /api/signup  { email }
// Appends the email to a JSON file in Vercel Blob. Zero external DB.
// Works locally / before setup by no-op'ing gracefully (returns ok:true, stored:false).
import { put, list, get } from '@vercel/blob'

export const config = { runtime: 'nodejs' }

const KEY = 'signups.json'

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST')
    return res.status(405).json({ ok: false, error: 'Method not allowed' })
  }

  let email = ''
  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : (req.body || {})
    email = String(body.email || '').trim().toLowerCase()
  } catch {
    return res.status(400).json({ ok: false, error: 'Bad JSON' })
  }

  const valid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  if (!valid) return res.status(400).json({ ok: false, error: 'Enter a valid email' })

  // No blob store configured yet → don't hard-fail the player, just skip storage.
  if (!process.env.BLOB_STORE_ID) {
    return res.status(200).json({ ok: true, stored: false, reason: 'blob-not-configured' })
  }

  try {
    // Read existing list (if any)
    let current = []
    try {
      const { blobs } = await list({ prefix: KEY })
      const hit = blobs.find(b => b.pathname === KEY)
      if (hit) {
        const result = await get(hit.url, { access: 'private' })
        const chunks = []
        for await (const chunk of result.stream) chunks.push(chunk)
        const text = Buffer.concat(chunks).toString('utf8')
        current = JSON.parse(text)
        if (!Array.isArray(current)) current = []
      }
    } catch { /* first write */ }

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
