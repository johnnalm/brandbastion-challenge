import { BotIcon, User, TrendingUp, MessageSquare, LightbulbIcon, ChevronRight } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"

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

interface ChatMessagesProps {
  messages: Message[]
  onSuggestedQuestion?: (question: string) => void
}

export function ChatMessages({ messages, onSuggestedQuestion }: ChatMessagesProps) {
  if (messages.length === 0) {
    return (
      <div className="flex justify-center items-center h-full animate-in fade-in-0 duration-500">
        <div className="text-center">
          <div className="inline-block p-4 bg-black/20 border border-white/10 rounded-full backdrop-blur-md">
            <BotIcon className="w-12 h-12 text-cyan-400" />
          </div>
          <h2 className="mt-6 text-2xl font-medium text-white">Analytics Agent</h2>
          <p className="mt-2 text-gray-400">Upload charts and comments to analyze your social media data.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-8 p-4 max-w-4xl mx-auto">
      {messages.map((message) => (
        <div key={message.id} className="animate-in slide-in-from-bottom-4 fade-in duration-500">
          {message.role === "user" ? (
            // User Message
            <div className="flex gap-4 items-start justify-end">
              <div className="rounded-2xl p-4 max-w-lg text-white backdrop-blur-lg border bg-blue-600/30 border-blue-500/30 rounded-br-none">
                <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center flex-shrink-0 shadow-lg">
                <User className="w-6 h-6 text-gray-300" />
              </div>
            </div>
          ) : (
            // Assistant Message
            <div className="space-y-4">
              <div className="flex gap-4 items-start">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-lg">
                  <BotIcon className="w-6 h-6 text-white" />
                </div>
                <div className="flex-1 space-y-4">
                  {/* Main Response */}
                  <div className="rounded-2xl p-4 text-white backdrop-blur-lg border bg-white/10 border-white/20 rounded-bl-none">
                    <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
                  </div>

                  {/* Insights Section */}
                  {message.metadata?.insights && message.metadata.insights.length > 0 && (
                    <Card className="bg-gradient-to-br from-emerald-500/10 to-teal-500/10 border-emerald-500/20 p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <LightbulbIcon className="w-5 h-5 text-emerald-400" />
                        <h3 className="font-semibold text-emerald-400">Key Insights</h3>
                      </div>
                      <ul className="space-y-2">
                        {message.metadata.insights.map((insight, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <TrendingUp className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                            <span className="text-gray-200 text-sm">{insight}</span>
                          </li>
                        ))}
                      </ul>
                    </Card>
                  )}

                  {/* Suggested Questions */}
                  {message.metadata?.suggested_questions && message.metadata.suggested_questions.length > 0 && (
                    <Card className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 border-purple-500/20 p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <MessageSquare className="w-5 h-5 text-purple-400" />
                        <h3 className="font-semibold text-purple-400">Follow-up Questions</h3>
                      </div>
                      <div className="space-y-2">
                        {message.metadata.suggested_questions.map((question, idx) => (
                          <Button
                            key={idx}
                            variant="ghost"
                            className="w-full justify-start text-left text-gray-200 hover:bg-purple-500/20 hover:text-white p-3 h-auto"
                            onClick={() => onSuggestedQuestion?.(question)}
                          >
                            <ChevronRight className="w-4 h-4 mr-2 flex-shrink-0" />
                            <span className="text-sm">{question}</span>
                          </Button>
                        ))}
                      </div>
                    </Card>
                  )}

                  {/* Clarification Needed */}
                  {message.metadata?.requires_clarification && (
                    <Card className="bg-gradient-to-br from-amber-500/10 to-orange-500/10 border-amber-500/20 p-4">
                      <p className="text-amber-400 text-sm">
                        ℹ️ I need more information to provide a complete analysis. Please ensure you&apos;ve uploaded relevant charts or pasted comments.
                      </p>
                    </Card>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}