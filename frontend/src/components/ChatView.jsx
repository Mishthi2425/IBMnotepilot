import React, { useState, useRef, useEffect } from 'react'
import { flushSync } from 'react-dom'
import Message from './Message'

const API = window.location.port === '5173' ? 'http://localhost:8000' : window.location.origin

export default function ChatView({ chat, onMenuClick, level, specific, uploadStatus }) {
  const [messages, setMessages] = useState(chat?.messages || [])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEnd = useRef(null)

  useEffect(() => {
    setMessages(chat?.messages || [])
  }, [chat?.id])

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async () => {
    if (!input.trim() || loading || !chat?.document_id) return
    const userMsg = { role: 'user', content: input.trim() }
    const allMsgs = [...messages, userMsg]
    setMessages(allMsgs)
    setInput('')
    setLoading(true)

    try {
      const prompt = specific ? `${input.trim()}\n\nInstruction: ${specific}` : input.trim()
      const finalMsgs = [...allMsgs.slice(0, -1), { role: 'user', content: prompt }]

      const res = await fetch(`${API}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: finalMsgs,
          document_id: chat.document_id,
          chat_id: chat.id,
          explanation_level: level
        })
      })

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let assistantMsg = { role: 'assistant', content: '', sources: [] }
      setMessages([...allMsgs, assistantMsg])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const text = decoder.decode(value)
        const lines = text.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6))
              if (event.type === 'token') {
                flushSync(() => {
                  assistantMsg = { ...assistantMsg, content: assistantMsg.content + event.content }
                  setMessages([...allMsgs, assistantMsg])
                })
              } else if (event.type === 'done') {
                flushSync(() => {
                  assistantMsg = { ...assistantMsg, sources: event.sources || [] }
                  setMessages([...allMsgs, assistantMsg])
                })
              }
            } catch {}
          }
        }
      }
    } catch (e) {
      setMessages([...allMsgs, { role: 'assistant', content: `Error: ${e.message}` }])
    } finally {
      setLoading(false)
    }
  }

  if (!chat) {
    return (
      <div className="chat-view">
        <div className="blob-container">
          <div className="blob blob-1" /><div className="blob blob-2" /><div className="blob blob-3" />
        </div>
        <div className="welcome">
          <div className="welcome-icon">+</div>
          <h1>NotePilot</h1>
          <p>AI powered personalized notes.</p>
          {uploadStatus.text && <div className={`upload-status ${uploadStatus.type}`} style={{ marginTop: 16 }}>{uploadStatus.text}</div>}
        </div>
      </div>
    )
  }

  return (
    <div className="chat-view">
      <div className="blob-container">
        <div className="blob blob-1" /><div className="blob blob-2" />
      </div>

      <div className="chat-header">
        <button className="menu-btn" onClick={onMenuClick}>=</button>
        <div className="chat-header-info">
          <h3>{chat.filename}</h3>
          <span>{messages.length} messages</span>
        </div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && !loading && (
          <div className="empty-chat">
            <div className="empty-chat-icon">?</div>
            <h3>Ask anything</h3>
            <p>Your document has been processed. Ask a question to get started.</p>
          </div>
        )}
        {messages.map((m, i) => <Message key={i} message={m} />)}
        {loading && messages[messages.length - 1]?.role !== 'assistant' && (
          <div className="loading-dots">
            <span>.</span><span>.</span><span>.</span>
          </div>
        )}
        <div ref={messagesEnd} />
      </div>

      <div className="chat-input-area">
        <div className="chat-input-row">
          <textarea
            className="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            placeholder="Ask something about your files..."
            rows={1}
            disabled={loading}
          />
          <button className="send-btn" onClick={send} disabled={loading || !input.trim()}>Send</button>
        </div>
      </div>
    </div>
  )
}
