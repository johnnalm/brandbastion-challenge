import type { UIMessage } from "@ai-sdk/react"
import { BotIcon, User } from "lucide-react"
import { cn } from "@/lib/utils"

export function ChatMessages({ messages }: { messages: UIMessage[] }) {
  if (messages.length === 0) {
    return (
      <div className="flex justify-center items-center h-full animate-in fade-in-0 duration-500">
        <div className="text-center">
          <div className="inline-block p-4 bg-black/20 border border-white/10 rounded-full backdrop-blur-md">
            <BotIcon className="w-12 h-12 text-cyan-400" />
          </div>
          <h2 className="mt-6 text-2xl font-medium text-white">AI Assistant</h2>
          <p className="mt-2 text-gray-400">Start the conversation by typing below.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-8 p-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={cn(
            "flex gap-4 items-start animate-in slide-in-from-bottom-4 fade-in duration-500",
            message.role === "user" ? "justify-end" : "justify-start",
          )}
        >
          {message.role === "assistant" && (
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-lg">
              <BotIcon className="w-6 h-6 text-white" />
            </div>
          )}
          <div
            className={cn(
              "rounded-2xl p-4 max-w-lg text-white backdrop-blur-lg border",
              message.role === "user"
                ? "bg-blue-600/30 border-blue-500/30 rounded-br-none"
                : "bg-white/10 border-white/20 rounded-bl-none",
            )}
          >
            <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
          </div>
          {message.role === "user" && (
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center flex-shrink-0 shadow-lg">
              <User className="w-6 h-6 text-gray-300" />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
