"use client"

import { useState, useEffect } from "react"
import { 
  MessageSquare, 
  Plus,
  Search,
  Sparkles,
  Trash2,
  MoreHorizontal
} from "lucide-react"
import { cn } from "@/lib/utils"

interface ChatHistory {
  id: string
  title: string
  lastMessage: string
  timestamp: Date
  isActive?: boolean
}

interface SidebarProps {
  currentChatId?: string
  onNewChat: () => void
  onSelectChat: (chatId: string) => void
}

export function Sidebar({ currentChatId, onNewChat, onSelectChat }: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [chatHistory, setChatHistory] = useState<ChatHistory[]>([])
  const [hoveredChat, setHoveredChat] = useState<string | null>(null)

  // Load chat history from localStorage
  useEffect(() => {
    const loadChatHistory = () => {
      const stored = localStorage.getItem('brandbastion_chat_history')
      if (stored) {
        try {
          const parsed = JSON.parse(stored)
          // Convert timestamp strings back to Date objects
          const history = parsed.map((chat: any) => ({
            ...chat,
            timestamp: new Date(chat.timestamp)
          }))
          setChatHistory(history)
        } catch (e) {
          console.error('Error loading chat history:', e)
          setChatHistory([])
        }
      }
    }
    
    loadChatHistory()
    // Listen for storage events to sync across tabs
    window.addEventListener('storage', loadChatHistory)
    // Also update when localStorage changes in the same tab
    const interval = setInterval(loadChatHistory, 1000)
    
    return () => {
      window.removeEventListener('storage', loadChatHistory)
      clearInterval(interval)
    }
  }, [currentChatId])

  const formatTimestamp = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 1) return "Just now"
    if (minutes < 60) return `${minutes}m ago`
    if (hours < 24) return `${hours}h ago`
    if (days === 1) return "Yesterday"
    if (days < 7) return `${days} days ago`
    return date.toLocaleDateString()
  }

  const filteredChats = chatHistory.filter(chat =>
    chat.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    chat.lastMessage.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const groupedChats = {
    today: filteredChats.filter(chat => {
      const diff = new Date().getTime() - chat.timestamp.getTime()
      return diff < 86400000 // Less than 24 hours
    }),
    yesterday: filteredChats.filter(chat => {
      const diff = new Date().getTime() - chat.timestamp.getTime()
      return diff >= 86400000 && diff < 172800000 // 24-48 hours
    }),
    older: filteredChats.filter(chat => {
      const diff = new Date().getTime() - chat.timestamp.getTime()
      return diff >= 172800000 // More than 48 hours
    })
  }

  const handleDeleteChat = (chatId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    const stored = localStorage.getItem('brandbastion_chat_history')
    if (stored) {
      try {
        const history = JSON.parse(stored)
        const filtered = history.filter((chat: any) => chat.id !== chatId)
        localStorage.setItem('brandbastion_chat_history', JSON.stringify(filtered))
        setChatHistory(filtered.map((chat: any) => ({
          ...chat,
          timestamp: new Date(chat.timestamp)
        })))
      } catch (e) {
        console.error('Error deleting chat:', e)
      }
    }
  }

  return (
    <aside className="w-80 h-screen bg-[#0A0A0A] border-r border-white/10 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-5 border-b border-white/10">
        <div className="flex items-center gap-2 px-4 py-2.5 text-sm font-semibold bg-gradient-to-r from-purple-600/20 to-blue-600/20 border border-purple-500/30 rounded-xl">
          <Sparkles className="w-4 h-4 text-purple-400" />
          <span className="text-white">BrandBastion</span>
        </div>
        
        <div className="relative">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center text-white font-semibold text-sm shadow-lg">
            BB
          </div>
          <div className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-400 rounded-full border-2 border-[#0A0A0A]"></div>
        </div>
      </div>

      {/* New Chat Button */}
      <div className="p-4">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all"
        >
          <Plus className="w-5 h-5" />
          <span>New Chat</span>
        </button>
      </div>

      {/* Search */}
      <div className="px-4 pb-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm placeholder-gray-500 text-white focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Chat History */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {/* Today */}
        {groupedChats.today.length > 0 && (
          <div className="mb-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-2">
              Today
            </p>
            <div className="space-y-1">
              {groupedChats.today.map((chat) => (
                <div
                  key={chat.id}
                  className="relative group"
                  onMouseEnter={() => setHoveredChat(chat.id)}
                  onMouseLeave={() => setHoveredChat(null)}
                >
                  <button
                    onClick={() => onSelectChat(chat.id)}
                    className={cn(
                      "w-full text-left px-3 py-3 rounded-lg transition-all",
                      currentChatId === chat.id
                        ? "bg-gradient-to-r from-purple-600/20 to-blue-600/20 border border-purple-500/30"
                        : "hover:bg-white/5"
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <MessageSquare className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm text-white truncate">
                          {chat.title}
                        </p>
                        <p className="text-xs text-gray-400 truncate mt-1">
                          {chat.lastMessage}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          {formatTimestamp(chat.timestamp)}
                        </p>
                      </div>
                    </div>
                  </button>
                  
                  {hoveredChat === chat.id && (
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                      <button className="p-1.5 hover:bg-white/10 rounded-md transition-colors">
                        <MoreHorizontal className="w-4 h-4 text-gray-400" />
                      </button>
                      <button 
                        onClick={(e) => handleDeleteChat(chat.id, e)}
                        className="p-1.5 hover:bg-white/10 rounded-md transition-colors"
                      >
                        <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-400" />
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Yesterday */}
        {groupedChats.yesterday.length > 0 && (
          <div className="mb-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-2">
              Yesterday
            </p>
            <div className="space-y-1">
              {groupedChats.yesterday.map((chat) => (
                <div
                  key={chat.id}
                  className="relative group"
                  onMouseEnter={() => setHoveredChat(chat.id)}
                  onMouseLeave={() => setHoveredChat(null)}
                >
                  <button
                    onClick={() => onSelectChat(chat.id)}
                    className={cn(
                      "w-full text-left px-3 py-3 rounded-lg transition-all",
                      currentChatId === chat.id
                        ? "bg-gradient-to-r from-purple-600/20 to-blue-600/20 border border-purple-500/30"
                        : "hover:bg-white/5"
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <MessageSquare className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm text-white truncate">
                          {chat.title}
                        </p>
                        <p className="text-xs text-gray-400 truncate mt-1">
                          {chat.lastMessage}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          {formatTimestamp(chat.timestamp)}
                        </p>
                      </div>
                    </div>
                  </button>
                  
                  {hoveredChat === chat.id && (
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                      <button className="p-1.5 hover:bg-white/10 rounded-md transition-colors">
                        <MoreHorizontal className="w-4 h-4 text-gray-400" />
                      </button>
                      <button 
                        onClick={(e) => handleDeleteChat(chat.id, e)}
                        className="p-1.5 hover:bg-white/10 rounded-md transition-colors"
                      >
                        <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-400" />
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Older */}
        {groupedChats.older.length > 0 && (
          <div className="mb-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-2">
              Previous
            </p>
            <div className="space-y-1">
              {groupedChats.older.map((chat) => (
                <div
                  key={chat.id}
                  className="relative group"
                  onMouseEnter={() => setHoveredChat(chat.id)}
                  onMouseLeave={() => setHoveredChat(null)}
                >
                  <button
                    onClick={() => onSelectChat(chat.id)}
                    className={cn(
                      "w-full text-left px-3 py-3 rounded-lg transition-all",
                      currentChatId === chat.id
                        ? "bg-gradient-to-r from-purple-600/20 to-blue-600/20 border border-purple-500/30"
                        : "hover:bg-white/5"
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <MessageSquare className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm text-white truncate">
                          {chat.title}
                        </p>
                        <p className="text-xs text-gray-400 truncate mt-1">
                          {chat.lastMessage}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          {formatTimestamp(chat.timestamp)}
                        </p>
                      </div>
                    </div>
                  </button>
                  
                  {hoveredChat === chat.id && (
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                      <button className="p-1.5 hover:bg-white/10 rounded-md transition-colors">
                        <MoreHorizontal className="w-4 h-4 text-gray-400" />
                      </button>
                      <button 
                        onClick={(e) => handleDeleteChat(chat.id, e)}
                        className="p-1.5 hover:bg-white/10 rounded-md transition-colors"
                      >
                        <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-400" />
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {filteredChats.length === 0 && (
          <div className="text-center py-8">
            <MessageSquare className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-sm text-gray-400">
              {searchQuery ? "No chats found" : "No conversations yet"}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Start a new chat to begin
            </p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-white/10">
        <div className="text-center text-xs text-gray-500">
          <span>Challenge</span>
        </div>
      </div>
    </aside>
  )
}