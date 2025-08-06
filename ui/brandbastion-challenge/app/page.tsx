"use client"

import { useState, useEffect } from "react"
import { PremiumChatInput, type FileWithPreview, type PastedContent } from "@/components/chat/premium-chat-input"
import { ChatMessages } from "@/components/chat/chat-messages"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { InfoIcon } from "lucide-react"
import { Sidebar } from "@/components/layout/sidebar"

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  metadata?: {
    insights?: string[]
    requires_clarification?: boolean
    suggested_questions?: string[]
  }
}

export default function AnalyticsChatPage() {
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState('')
  const [currentChatId, setCurrentChatId] = useState<string>(() => {
    // Initialize with current timestamp for new chat
    return Date.now().toString()
  })
  
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })
  const [isClient, setIsClient] = useState(false)

  useEffect(() => {
    setIsClient(true)
    const handleMouseMove = (event: MouseEvent) => {
      setMousePosition({ x: event.clientX, y: event.clientY })
    }
    window.addEventListener("mousemove", handleMouseMove)
    return () => window.removeEventListener("mousemove", handleMouseMove)
  }, [])

  const handleNewChat = () => {
    // Clear current conversation and start new
    setMessages([])
    setConversationId(null)
    setCurrentStreamingMessage('')
    const newChatId = Date.now().toString()
    setCurrentChatId(newChatId)
    
    // Clear localStorage for new chat
    localStorage.removeItem('current_conversation_id')
    localStorage.removeItem('current_messages')
  }

  const handleSelectChat = (chatId: string) => {
    // Load chat history for selected chat
    setCurrentChatId(chatId)
    
    // Load messages from localStorage for this chat
    const history = localStorage.getItem('brandbastion_chat_history')
    if (history) {
      try {
        const allChats = JSON.parse(history)
        const selectedChat = allChats.find((chat: any) => chat.id === chatId)
        if (selectedChat && selectedChat.messages) {
          setMessages(selectedChat.messages)
          setConversationId(selectedChat.conversationId || null)
        } else {
          setMessages([])
        }
      } catch (e) {
        console.error('Error loading chat:', e)
        setMessages([])
      }
    }
  }

  // Save chat to history when messages change
  useEffect(() => {
    if (messages.length > 0) {
      const saveToHistory = () => {
        const history = localStorage.getItem('brandbastion_chat_history') || '[]'
        try {
          const allChats = JSON.parse(history)
          const existingIndex = allChats.findIndex((chat: any) => chat.id === currentChatId)
          
          const firstUserMessage = messages.find(m => m.role === 'user')?.content || 'New Chat'
          const lastMessage = messages[messages.length - 1]
          
          const chatData = {
            id: currentChatId,
            title: firstUserMessage.substring(0, 50) + (firstUserMessage.length > 50 ? '...' : ''),
            lastMessage: lastMessage.content.substring(0, 100) + (lastMessage.content.length > 100 ? '...' : ''),
            timestamp: new Date().toISOString(),
            messages: messages,
            conversationId: conversationId
          }
          
          if (existingIndex !== -1) {
            allChats[existingIndex] = chatData
          } else {
            allChats.unshift(chatData)
          }
          
          // Keep only last 50 chats
          const trimmedChats = allChats.slice(0, 50)
          localStorage.setItem('brandbastion_chat_history', JSON.stringify(trimmedChats))
        } catch (e) {
          console.error('Error saving chat history:', e)
        }
      }
      
      saveToHistory()
    }
  }, [messages, currentChatId, conversationId])

  const handleSendMessage = async (message: string, files: FileWithPreview[], pastedContent: PastedContent[], model?: string) => {
    // Process files and extract charts/comments
    const charts: string[] = []
    const comments: string[] = []
    
    // Process uploaded files (PDFs)
    for (const file of files) {
      if (file.file.type === 'application/pdf' || file.file.name.endsWith('.pdf')) {
        // For now, we'll send the file content as text if available
        if (file.textContent) {
          charts.push(file.textContent)
        } else {
          charts.push(`[PDF: ${file.file.name}]`)
        }
      }
    }
    
    // Process pasted content as comments
    for (const pasted of pastedContent) {
      // Split by newlines in case multiple comments are pasted
      const lines = pasted.content.split('\n').filter(line => line.trim())
      comments.push(...lines)
    }
    
    // Files and comments are processed but not stored for reference
    
    // Prepare the message content
    let displayMessage = message
    if (charts.length > 0) {
      displayMessage += `\n\n📊 ${charts.length} chart(s) attached`
    }
    if (comments.length > 0) {
      displayMessage += `\n\n💬 ${comments.length} comment(s) included`
    }
    
    // Add user message immediately
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: displayMessage
    }
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)
    setCurrentStreamingMessage('')
    
    // Send to backend directly
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          conversation_id: conversationId,
          charts: charts,
          comments: comments,
          model: model
        })
      })

      if (!response.ok) {
        throw new Error('Failed to send message')
      }

      // Handle SSE stream
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let assistantMessage = ''
      let metadata: any = null

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim()
              if (data && data !== '[DONE]') {
                try {
                  const event = JSON.parse(data)
                  console.log('SSE Event:', event)

                  if (event.type === 'text') {
                    assistantMessage += event.text
                    setCurrentStreamingMessage(assistantMessage)
                  } else if (event.type === 'data' && event.data) {
                    metadata = event.data
                    console.log('Received metadata:', metadata)
                    if (!conversationId && metadata.conversationId) {
                      setConversationId(metadata.conversationId)
                    }
                  }
                } catch (e) {
                  console.error('Error parsing SSE event:', e, data)
                }
              }
            }
          }
        }
      }

      // Add final assistant message
      const assistantMessageObj: Message = {
        id: Date.now().toString() + '_assistant',
        role: 'assistant',
        content: assistantMessage,
        metadata: metadata
      }
      
      console.log('Final assistant message:', assistantMessageObj)
      setMessages(prev => [...prev, assistantMessageObj])
      setCurrentStreamingMessage('')
      setIsLoading(false)
      
    } catch (error) {
      console.error('Error sending message:', error)
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen w-full bg-[#0A0A0A]">
      {/* Sidebar */}
      <Sidebar 
        currentChatId={currentChatId}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
      />
      
      {/* Main Content Area */}
      <div className="relative flex-1 overflow-hidden">
        {/* Interactive Spotlight Background */}
        {isClient && (
          <div
            className="pointer-events-none absolute -inset-px z-0 transition duration-300"
            style={{
              background: `radial-gradient(600px at ${mousePosition.x}px ${mousePosition.y}px, rgba(29, 78, 216, 0.15), transparent 80%)`,
            }}
          />
        )}

        <main className="relative z-10 flex h-screen flex-col">

        {/* Instructions Alert - Moved up to show first */}
        {messages.length === 0 && (
          <div className="max-w-4xl mx-auto p-4 pt-8">
            <Alert className="bg-blue-500/10 border-blue-500/20">
              <InfoIcon className="h-4 w-4 text-blue-400" />
              <AlertDescription className="text-gray-300">
                <strong>How to use:</strong>
                <ul className="list-disc list-inside mt-2 space-y-1">
                  <li>Upload PDF charts using the + button or drag & drop</li>
                  <li>Paste user comments directly into the chat input</li>
                  <li>Ask analytical questions about your social media data</li>
                  <li>Get insights on engagement, sentiment, and trends</li>
                </ul>
              </AlertDescription>
            </Alert>
          </div>
        )}

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4">
          <ChatMessages 
            messages={[...messages, ...(currentStreamingMessage ? [{
              id: 'streaming',
              role: 'assistant' as const,
              content: currentStreamingMessage
            }] : [])]} 
            onSuggestedQuestion={(question) => {
              handleSendMessage(question, [], [])
            }}
          />
        </div>

        {/* Chat Input */}
        <div className="w-full max-w-4xl mx-auto p-4">
          <PremiumChatInput 
            onSendMessage={handleSendMessage}
            disabled={isLoading}
            placeholder="Ask about metrics, trends, or user sentiment..."
            maxFiles={10}
            maxFileSize={10 * 1024 * 1024} // 10MB
          />
        </div>
      </main>
      </div>
    </div>
  )
}