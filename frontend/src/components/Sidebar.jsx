import React, { useRef } from 'react'

export default function Sidebar({ chats, activeChatId, onSelectChat, onNewChat, onDeleteChat, isOpen, onClose, onUpload, level, setLevel, specific, setSpecific, onClearChats }) {
  const fileRef = useRef(null)

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    onUpload(file)
    e.target.value = ''
  }

  return (
    <>
      <div className={`sidebar-overlay ${isOpen ? 'open' : ''}`} onClick={onClose} />
      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-section">
          <div className="sidebar-label">Upload PDFs or DOCX files</div>
          <div className="sidebar-upload" onClick={() => fileRef.current?.click()}>
            <div className="sidebar-upload-btn">Upload</div>
            <span>PDF, DOCX, TXT</span>
            <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" onChange={handleUpload} hidden />
          </div>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-label">How should I answer?</div>
          <select className="sidebar-select" value={level} onChange={e => setLevel(e.target.value)}>
            <option value="basic">Concise answer</option>
            <option value="detailed">Detailed answer</option>
            <option value="comprehensive">Bullet points</option>
          </select>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-label">Anything specific? (optional)</div>
          <input
            className="sidebar-input"
            type="text"
            placeholder="e.g. explain like I'm 5"
            value={specific}
            onChange={e => setSpecific(e.target.value)}
          />
        </div>

        <div className="sidebar-divider" />

        <button className="sidebar-new-chat" onClick={onNewChat}>+ New chat</button>

        <div className="sidebar-label" style={{ padding: '10px 16px 4px' }}>Your chats</div>
        <div className="sidebar-chats">
          {chats.length === 0 && (
            <div className="sidebar-empty">No chats yet</div>
          )}
          {chats.map(chat => (
            <div
              key={chat.id}
              className={`chat-item ${activeChatId === chat.id ? 'active' : ''}`}
              onClick={() => { onSelectChat(chat.id); onClose(); }}
            >
              <div className="chat-item-dot" />
              <div className="chat-item-text">
                <div className="chat-item-name">{chat.filename}</div>
              </div>
              <button
                className="chat-item-delete"
                onClick={(e) => { e.stopPropagation(); onDeleteChat(chat.id); }}
              >
                x
              </button>
            </div>
          ))}
        </div>

        <button className="sidebar-clear" onClick={onClearChats}>Clear chat</button>
      </aside>
    </>
  )
}
