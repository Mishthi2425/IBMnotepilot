import React, { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import ChatView from './components/ChatView'

const API = window.location.port === '5173' ? 'http://localhost:8000' : window.location.origin

export default function App() {
  const [chats, setChats] = useState([])
  const [activeChatId, setActiveChatId] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [level, setLevel] = useState('detailed')
  const [specific, setSpecific] = useState('')
  const [uploadStatus, setUploadStatus] = useState({ type: '', text: '' })

  useEffect(() => { fetchChats() }, [])

  const fetchChats = async () => {
    try {
      const res = await fetch(`${API}/chats`)
      if (res.ok) {
        const data = await res.json()
        const normalized = (data.chats || []).map(c => ({
          id: c.chat_id,
          document_id: c.document_id,
          filename: c.filename,
          messages: c.messages || []
        }))
        setChats(normalized)
      }
    } catch {}
  }

  const handleUpload = async (file) => {
    setUploadStatus({ type: 'loading', text: `Processing ${file.name}...` })
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch(`${API}/upload`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error((await res.json()).detail || 'Upload failed')
      const d = await res.json()
      const newChat = { id: d.chat_id, document_id: d.document_id, filename: d.filename, messages: [] }
      setChats(prev => [newChat, ...prev])
      setActiveChatId(d.chat_id)
      setUploadStatus({ type: 'success', text: `${d.filename} ready` })
      setTimeout(() => setUploadStatus({ type: '', text: '' }), 3000)
    } catch (e) {
      setUploadStatus({ type: 'error', text: e.message })
    }
  }

  const handleNewChat = () => {
    setActiveChatId(null)
    setSidebarOpen(false)
  }

  const handleDeleteChat = async (chatId) => {
    try {
      await fetch(`${API}/chat/${chatId}`, { method: 'DELETE' })
      setChats(prev => prev.filter(c => c.id !== chatId))
      if (activeChatId === chatId) setActiveChatId(null)
    } catch {}
  }

  const handleClearChats = async () => {
    for (const chat of chats) {
      try { await fetch(`${API}/chat/${chat.id}`, { method: 'DELETE' }) } catch {}
    }
    setChats([])
    setActiveChatId(null)
  }

  const activeChat = chats.find(c => c.id === activeChatId) || null

  return (
    <div className="app-layout">
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        onSelectChat={setActiveChatId}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
        onUpload={handleUpload}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        level={level}
        setLevel={setLevel}
        specific={specific}
        setSpecific={setSpecific}
        onClearChats={handleClearChats}
      />
      <ChatView
        chat={activeChat}
        onMenuClick={() => setSidebarOpen(true)}
        level={level}
        specific={specific}
        uploadStatus={uploadStatus}
      />
    </div>
  )
}
