import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight(code: string, lang: string): string {
    const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
    try {
      return (
        '<pre class="md-code-block"><code>' +
        hljs.highlight(code, { language, ignoreIllegals: true }).value +
        '</code></pre>'
      )
    } catch {
      return '<pre class="md-code-block"><code>' + md.utils.escapeHtml(code) + '</code></pre>'
    }
  },
})

export function renderMarkdown(content: string): string {
  return md.render(content || '')
}
