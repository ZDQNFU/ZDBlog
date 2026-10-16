export function safeMarkdown(html) {
  const doc = new DOMParser().parseFromString(html, 'text/html')
  const allowed = new Set([
    'P',
    'BR',
    'STRONG',
    'EM',
    'DEL',
    'S',
    'CODE',
    'PRE',
    'BLOCKQUOTE',
    'UL',
    'OL',
    'LI',
    'H1',
    'H2',
    'H3',
    'H4',
    'H5',
    'H6',
    'HR',
    'TABLE',
    'THEAD',
    'TBODY',
    'TR',
    'TH',
    'TD',
    'A',
  ])
  for (const el of [...doc.body.querySelectorAll('*')]) {
    if (!allowed.has(el.tagName)) {
      el.replaceWith(doc.createTextNode(el.textContent || ''))
      continue
    }
    const href = el.tagName === 'A' ? el.getAttribute('href') : null
    for (const attr of [...el.attributes]) el.removeAttribute(attr.name)
    if (href) {
      try {
        const url = new URL(href, window.location.origin)
        if (['http:', 'https:', 'mailto:'].includes(url.protocol)) {
          el.setAttribute('href', url.href)
          el.setAttribute('target', '_blank')
          el.setAttribute('rel', 'noopener noreferrer')
        }
      } catch {
        /* Invalid links are rendered as plain text. */
      }
    }
  }
  return doc.body.innerHTML
}
