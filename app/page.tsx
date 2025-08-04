"use client"

import { useState, useEffect } from "react"
import { useChat } from "@ai-sdk/react"
import { PremiumChatInput, type FileWithPreview, type PastedContent } from "@/components/chat/premium-chat-input"
import { ChatMessages } from "@/components/chat/chat-messages"

export default function PremiumChatPage() {
  const { messages, append } = useChat({ api: "/api/chat" })
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

  const handleSendMessage = (message: string, files: FileWithPreview[], pastedContent: PastedContent[]) => {
    let combinedContent = message
    if (files.length > 0) combinedContent += `\n\n[${files.length} file(s) attached]`
    if (pastedContent.length > 0) combinedContent += `\n\n[${pastedContent.length} pasted content block(s)]`
    append({ role: "user", content: combinedContent })
  }

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-[#0A0A0A]">
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
        <div className="flex-1 overflow-y-auto p-4">
          <ChatMessages messages={messages} />
        </div>
        <div className="w-full max-w-4xl mx-auto p-4">
          <PremiumChatInput onSendMessage={handleSendMessage} />
        </div>
      </main>
    </div>
  )
}
