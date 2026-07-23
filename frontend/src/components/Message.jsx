import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'

function cleanLatex(text) {
  if (!text) return text
  return text
    .replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, '($1)/($2)')
    .replace(/\\sqrt\{([^}]+)\}/g, 'sqrt($1)')
    .replace(/\\hat\{([^}]+)\}/g, '$1')
    .replace(/\\bar\{([^}]+)\}/g, '$1')
    .replace(/\\partial/g, 'd/d')
    .replace(/\\sum(?:_\{[^}]*\})?(?:\^\{[^}]*\})?/g, 'sum')
    .replace(/\\prod(?:_\{[^}]*\})?(?:\^\{[^}]*\})?/g, 'product')
    .replace(/\\leftarrow/g, '<-')
    .replace(/\\rightarrow/g, '->')
    .replace(/\\cdot/g, '*')
    .replace(/\\times/g, 'x')
    .replace(/\\alpha/g, 'alpha')
    .replace(/\\beta/g, 'beta')
    .replace(/\\gamma/g, 'gamma')
    .replace(/\\lambda/g, 'lambda')
    .replace(/\\sigma/g, 'sigma')
    .replace(/\\theta/g, 'theta')
    .replace(/\\omega/g, 'omega')
    .replace(/\\epsilon/g, 'epsilon')
    .replace(/\\delta/g, 'delta')
    .replace(/\\eta/g, 'eta')
    .replace(/\\mu/g, 'mu')
    .replace(/\\rho/g, 'rho')
    .replace(/\\tau/g, 'tau')
    .replace(/\\phi/g, 'phi')
    .replace(/\\pi/g, 'pi')
    .replace(/\\infty/g, 'infinity')
    .replace(/\\leq/g, '<=')
    .replace(/\\geq/g, '>=')
    .replace(/\\neq/g, '!=')
    .replace(/\\approx/g, '~')
    .replace(/\\pm/g, '+/-')
    .replace(/\\mp(g)?/g, '-/+')
    .replace(/\\forall/g, 'for all')
    .replace(/\\exists/g, 'there exists')
    .replace(/\\nabla/g, 'gradient')
    .replace(/\\in/g, 'in')
    .replace(/\\notin/g, 'not in')
    .replace(/\\subset/g, 'subset')
    .replace(/\\cup/g, 'union')
    .replace(/\\cap/g, 'intersection')
    .replace(/\\emptyset/g, 'empty set')
    .replace(/\\\(/g, '')
    .replace(/\\\)/g, '')
    .replace(/\\\[/g, '')
    .replace(/\\\]/g, '')
    .replace(/\{([^}]+)\}/g, '$1')
    .replace(/_/g, '')
    .replace(/\^/g, '')
    .replace(/\\\\/g, '')
    .replace(/\\([a-zA-Z]+)/g, '$1')
    .replace(/\|\|/g, ' | ')
    .replace(/<br>/g, '\n')
}

export default function Message({ message }) {
  const [showSources, setShowSources] = useState(false)
  const [copied, setCopied] = useState(false)

  const copyAnswer = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const cleanedContent = cleanLatex(message.content)

  return (
    <div className={`message ${message.role}`}>
      <div className="message-role">
        {message.role === 'user' ? 'You' : 'NotePilot'}
      </div>
      <div className="message-content">
        <ReactMarkdown>{cleanedContent}</ReactMarkdown>
      </div>
      {message.role === 'assistant' && (
        <div className="message-footer">
          <button className="copy-btn" onClick={copyAnswer}>
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
      )}
      {message.sources && message.sources.length > 0 && (
        <details className="message-sources">
          <summary onClick={(e) => { e.preventDefault(); setShowSources(!showSources) }}>
            Sources ({message.sources.length})
          </summary>
          {showSources && message.sources.map((s, i) => (
            <div key={i} className="source-item">{s.content}</div>
          ))}
        </details>
      )}
    </div>
  )
}
