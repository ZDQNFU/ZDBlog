export function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^\w一-鿿\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}

export function extractTOCFromMarkdown(md) {
  if (!md) return []
  const items = []
  const lines = md.split('\n')
  for (const line of lines) {
    const match = line.match(/^(#{1,3})\s+(.+)$/)
    if (match) {
      const text = match[2].trim()
      items.push({ id: slugify(text), level: match[1].length, text })
    }
  }
  return items
}

export function extractTOCFromContainer(container) {
  if (!container) return []
  const headings = container.querySelectorAll('h1, h2, h3')
  return Array.from(headings)
    .filter(h => h.id && h.textContent.trim())
    .map(h => ({
      id: h.id,
      level: parseInt(h.tagName[1]),
      text: h.textContent.trim(),
    }))
}
