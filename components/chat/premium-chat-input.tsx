"use client"

import type React from "react"
import { useState, useRef, useEffect, useCallback } from "react"
import { Plus, ArrowUp, X, FileText, Loader2, Copy, SlidersHorizontal, ChevronDown, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

// All types and helper functions from your previous prompt are preserved here.
export interface FileWithPreview {
  id: string
  file: File
  preview?: string
  type: string
  uploadStatus: "pending" | "uploading" | "complete" | "error"
  textContent?: string
}
export interface PastedContent {
  id: string
  content: string
  timestamp: Date
  wordCount: number
}
export interface ModelOption {
  id: string
  name: string
  description: string
  badge?: string
}
interface ChatInputProps {
  onSendMessage?: (message: string, files: FileWithPreview[], pastedContent: PastedContent[]) => void
  disabled?: boolean
  placeholder?: string
  maxFiles?: number
  maxFileSize?: number
  models?: ModelOption[]
  defaultModel?: string
  onModelChange?: (modelId: string) => void
}
const MAX_FILES = 10
const MAX_FILE_SIZE = 50 * 1024 * 1024
const PASTE_THRESHOLD = 200
const DEFAULT_MODELS_INTERNAL: ModelOption[] = [
  { id: "claude-sonnet-4", name: "Claude Sonnet 4", description: "Balanced model", badge: "Latest" },
  { id: "claude-opus-3.5", name: "Claude Opus 3.5", description: "Highest intelligence" },
  { id: "claude-haiku-3", name: "Claude Haiku 3", description: "Fastest responses" },
]
const isTextualFile = (file: File): boolean => {
  const textualTypes = [
    "text/",
    "application/json",
    "application/xml",
    "application/javascript",
    "application/typescript",
  ]
  const textualExtensions = [
    "txt",
    "md",
    "py",
    "js",
    "ts",
    "jsx",
    "tsx",
    "html",
    "css",
    "json",
    "xml",
    "yaml",
    "csv",
    "sql",
  ]
  const isTextualMimeType = textualTypes.some((type) => file.type.toLowerCase().startsWith(type))
  const extension = file.name.split(".").pop()?.toLowerCase() || ""
  return isTextualMimeType || textualExtensions.includes(extension)
}
const readFileAsText = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve((e.target?.result as string) || "")
    reader.onerror = (e) => reject(e)
    reader.readAsText(file)
  })
}

// Premium Styled Sub-components
const FilePreviewCard: React.FC<{ file: FileWithPreview; onRemove: (id: string) => void }> = ({ file, onRemove }) => {
  return (
    <div className="relative group w-28 h-28 bg-black/20 border border-white/10 rounded-xl flex-shrink-0 overflow-hidden backdrop-blur-md animate-in fade-in zoom-in-95 duration-300">
      {file.type.startsWith("image/") && file.preview ? (
        <img src={file.preview || "/placeholder.svg"} alt={file.file.name} className="w-full h-full object-cover" />
      ) : (
        <div className="flex flex-col items-center justify-center h-full p-2 text-center">
          <FileText className="h-8 w-8 text-gray-400" />
          <p className="text-xs text-gray-300 mt-2 truncate" title={file.file.name}>
            {file.file.name}
          </p>
        </div>
      )}
      {file.uploadStatus === "uploading" && (
        <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-cyan-400" />
        </div>
      )}
      <Button
        size="icon"
        variant="ghost"
        className="absolute top-1.5 right-1.5 h-7 w-7 p-0 bg-black/40 hover:bg-black/60 text-white rounded-full opacity-0 group-hover:opacity-100 transition-all hover:scale-110"
        onClick={() => onRemove(file.id)}
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  )
}

const PastedContentCard: React.FC<{ content: PastedContent; onRemove: (id: string) => void }> = ({
  content,
  onRemove,
}) => {
  return (
    <div className="relative group w-28 h-28 bg-black/20 border border-white/10 rounded-xl flex-shrink-0 overflow-hidden backdrop-blur-md p-2 animate-in fade-in zoom-in-95 duration-300">
      <p className="text-xs text-gray-300 break-words overflow-hidden h-full">{content.content}</p>
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent" />
      <div className="absolute bottom-2 left-2 text-xs font-bold text-cyan-300">PASTED</div>
      <div className="absolute top-1.5 right-1.5 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
        <Button
          size="icon"
          variant="ghost"
          className="h-7 w-7 p-0 bg-black/40 hover:bg-black/60 text-white rounded-full transition-transform hover:scale-110"
          onClick={() => navigator.clipboard.writeText(content.content)}
        >
          <Copy className="h-3.5 w-3.5" />
        </Button>
        <Button
          size="icon"
          variant="ghost"
          className="h-7 w-7 p-0 bg-black/40 hover:bg-black/60 text-white rounded-full transition-transform hover:scale-110"
          onClick={() => onRemove(content.id)}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

const ModelSelector: React.FC<{
  models: ModelOption[]
  selectedModel: string
  onModelChange: (id: string) => void
}> = ({ models, selectedModel, onModelChange }) => {
  const [isOpen, setIsOpen] = useState(false)
  const selected = models.find((m) => m.id === selectedModel) || models[0]
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setIsOpen(false)
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  return (
    <div className="relative" ref={ref}>
      <Button
        variant="ghost"
        onClick={() => setIsOpen(!isOpen)}
        className="text-gray-300 hover:bg-white/10 hover:text-white"
      >
        {selected.name}
        <ChevronDown className={`ml-2 h-4 w-4 transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </Button>
      {isOpen && (
        <div className="absolute bottom-full right-0 mb-2 w-72 bg-gray-950/90 border border-white/10 rounded-lg shadow-2xl backdrop-blur-xl z-20 p-2 animate-in fade-in-0 zoom-in-95">
          {models.map((model) => (
            <button
              key={model.id}
              onClick={() => {
                onModelChange(model.id)
                setIsOpen(false)
              }}
              className={cn(
                "w-full text-left p-2.5 rounded-md hover:bg-white/10 transition-colors flex items-center justify-between",
                model.id === selectedModel && "bg-white/10",
              )}
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium text-white">{model.name}</span>
                  {model.badge && (
                    <span className="px-1.5 py-0.5 text-xs bg-cyan-500/20 text-cyan-300 rounded">{model.badge}</span>
                  )}
                </div>
                <p className="text-xs text-gray-400 mt-0.5">{model.description}</p>
              </div>
              {model.id === selectedModel && <Check className="h-4 w-4 text-cyan-400" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export const PremiumChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  disabled = false,
  placeholder = "Message your AI assistant...",
  maxFiles = MAX_FILES,
  maxFileSize = MAX_FILE_SIZE,
  models = DEFAULT_MODELS_INTERNAL,
  defaultModel,
  onModelChange,
}) => {
  const [message, setMessage] = useState("")
  const [files, setFiles] = useState<FileWithPreview[]>([])
  const [pastedContent, setPastedContent] = useState<PastedContent[]>([])
  const [selectedModel, setSelectedModel] = useState(defaultModel || models[0]?.id || "")
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // All logic hooks are preserved from your prompt.
  const handleFileSelect = useCallback(
    (selectedFiles: FileList | null) => {
      if (!selectedFiles) return
      const newFiles = Array.from(selectedFiles)
        .slice(0, maxFiles - files.length)
        .map((file) => ({
          id: crypto.randomUUID(),
          file,
          preview: file.type.startsWith("image/") ? URL.createObjectURL(file) : undefined,
          type: file.type,
          uploadStatus: "pending" as const,
        }))
      setFiles((prev) => [...prev, ...newFiles])
      newFiles.forEach((f) => {
        if (isTextualFile(f.file)) {
          readFileAsText(f.file).then((textContent) => {
            setFiles((prev) => prev.map((pf) => (pf.id === f.id ? { ...pf, textContent } : pf)))
          })
        }
        setFiles((prev) => prev.map((pf) => (pf.id === f.id ? { ...pf, uploadStatus: "uploading" } : pf)))
        setTimeout(() => {
          setFiles((prev) => prev.map((pf) => (pf.id === f.id ? { ...pf, uploadStatus: "complete" } : pf)))
        }, 1500)
      })
    },
    [files.length, maxFiles],
  )
  const removeFile = useCallback((id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id))
  }, [])
  const handlePaste = useCallback(
    (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
      const textData = e.clipboardData.getData("text")
      if (textData && textData.length > PASTE_THRESHOLD && pastedContent.length < 5) {
        e.preventDefault()
        setPastedContent((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            content: textData,
            timestamp: new Date(),
            wordCount: textData.split(/\s+/).length,
          },
        ])
      }
    },
    [pastedContent.length],
  )
  const handleSend = useCallback(() => {
    if (disabled || (!message.trim() && files.length === 0 && pastedContent.length === 0)) return
    onSendMessage?.(message, files, pastedContent)
    setMessage("")
    setFiles([])
    setPastedContent([])
  }, [message, files, pastedContent, disabled, onSendMessage])
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [message])

  const canSend = !disabled && (message.trim() || files.length > 0 || pastedContent.length > 0)

  return (
    <div className="relative">
      <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-2xl blur-lg opacity-20"></div>
      <div className="relative z-10 bg-black/60 p-2 border border-white/10 rounded-2xl shadow-2xl shadow-black/40 backdrop-blur-xl focus-within:border-cyan-400/50 focus-within:ring-2 focus-within:ring-cyan-400/20 transition-all duration-300">
        {(files.length > 0 || pastedContent.length > 0) && (
          <div className="p-2 border-b border-white/10">
            <div className="flex gap-4 overflow-x-auto pb-2">
              {pastedContent.map((pc) => (
                <PastedContentCard
                  key={pc.id}
                  content={pc}
                  onRemove={(id) => setPastedContent((p) => p.filter((item) => item.id !== id))}
                />
              ))}
              {files.map((file) => (
                <FilePreviewCard key={file.id} file={file} onRemove={removeFile} />
              ))}
            </div>
          </div>
        )}
        <div className="p-2">
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder={placeholder}
            disabled={disabled}
            className="w-full max-h-48 bg-transparent border-none text-gray-200 placeholder:text-gray-500 focus:ring-0 resize-none text-lg"
            rows={1}
          />
        </div>
        <div className="flex items-center justify-between p-2">
          <div className="flex items-center gap-1">
            <Button
              size="icon"
              variant="ghost"
              className="text-gray-400 hover:text-white hover:bg-white/10 transition-transform hover:scale-110"
              onClick={() => fileInputRef.current?.click()}
            >
              <Plus className="h-5 w-5" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="text-gray-400 hover:text-white hover:bg-white/10 transition-transform hover:scale-110"
            >
              <SlidersHorizontal className="h-5 w-5" />
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <ModelSelector models={models} selectedModel={selectedModel} onModelChange={setSelectedModel} />
            <Button
              size="icon"
              onClick={handleSend}
              disabled={!canSend}
              className={cn(
                "rounded-full w-10 h-10 transition-all duration-300",
                canSend
                  ? "bg-cyan-500 text-white shadow-[0_0_20px_theme(colors.cyan.500/60%)] hover:bg-cyan-400 animate-pulse"
                  : "bg-white/10 text-gray-500 cursor-not-allowed",
              )}
            >
              <ArrowUp className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={(e) => handleFileSelect(e.target.files)}
      />
    </div>
  )
}
