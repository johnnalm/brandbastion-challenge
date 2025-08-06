"use client"

import type React from "react"
import { useState, useRef, useEffect, useCallback } from "react"
import { Plus, ArrowUp, X, FileText, ImageIcon, Loader2, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import Image from "next/image"

export interface FileWithPreview {
  id: string
  file: File
  preview?: string
  uploadStatus: "pending" | "uploading" | "complete" | "error"
}

interface ChatInputProps {
  onSendMessage: (message: string, files: FileWithPreview[]) => void
  disabled?: boolean
  placeholder?: string
  maxFiles?: number
  maxFileSize?: number // in bytes
}

const MAX_FILES = 5
const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB



const FilePreviewCard: React.FC<{
  file: FileWithPreview
  onRemove: (id: string) => void
}> = ({ file, onRemove }) => {
  const isImage = file.file.type.startsWith("image/")

  return (
    <div className="relative group w-24 h-24 bg-gray-100 border border-gray-200 rounded-lg flex-shrink-0 overflow-hidden">
      {isImage && file.preview ? (
        <Image src={file.preview || "/placeholder.svg"} alt={file.file.name} className="w-full h-full object-cover" width={96} height={96} />
      ) : (
        <div className="flex flex-col items-center justify-center h-full p-2 text-center">
          <FileText className="h-6 w-6 text-gray-500" />
          <p className="text-xs text-gray-600 mt-1 truncate" title={file.file.name}>
            {file.file.name}
          </p>
        </div>
      )}
      {file.uploadStatus === "uploading" && (
        <div className="absolute inset-0 bg-white/70 flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
        </div>
      )}
      {file.uploadStatus === "error" && (
        <div className="absolute inset-0 bg-red-500/20 flex items-center justify-center">
          <AlertCircle className="h-6 w-6 text-red-600" />
        </div>
      )}
      <Button
        size="icon"
        variant="ghost"
        className="absolute top-0.5 right-0.5 h-6 w-6 p-0 bg-black/20 hover:bg-black/40 text-white opacity-0 group-hover:opacity-100 rounded-full"
        onClick={() => onRemove(file.id)}
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  )
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  disabled = false,
  placeholder = "Ask about social engagement...",
  maxFiles = MAX_FILES,
  maxFileSize = MAX_FILE_SIZE,
}) => {
  const [message, setMessage] = useState("")
  const [files, setFiles] = useState<FileWithPreview[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      const maxHeight = 120
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, maxHeight)}px`
    }
  }, [message])

  const handleFileSelect = useCallback(
    (selectedFiles: FileList | null) => {
      if (!selectedFiles) return
      const filesToAdd = Array.from(selectedFiles).slice(0, maxFiles - files.length)

      const newFiles = filesToAdd
        .filter((file) => file.size <= maxFileSize)
        .map((file) => ({
          id: crypto.randomUUID(),
          file,
          preview: file.type.startsWith("image/") ? URL.createObjectURL(file) : undefined,
          uploadStatus: "pending" as const,
        }))

      setFiles((prev) => [...prev, ...newFiles])

      // Simulate upload
      newFiles.forEach((fileToUpload) => {
        setFiles((prev) => prev.map((f) => (f.id === fileToUpload.id ? { ...f, uploadStatus: "uploading" } : f)))
        setTimeout(
          () => {
            setFiles((prev) => prev.map((f) => (f.id === fileToUpload.id ? { ...f, uploadStatus: "complete" } : f)))
          },
          1000 + Math.random() * 2000,
        )
      })
    },
    [files.length, maxFiles, maxFileSize],
  )

  const removeFile = useCallback((id: string) => {
    setFiles((prev) => {
      const fileToRemove = prev.find((f) => f.id === id)
      if (fileToRemove?.preview) {
        URL.revokeObjectURL(fileToRemove.preview)
      }
      return prev.filter((f) => f.id !== id)
    })
  }, [])

  const handleDragEvent = (e: React.DragEvent, entering: boolean) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(entering)
  }

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      handleDragEvent(e, false)
      if (e.dataTransfer.files) {
        handleFileSelect(e.dataTransfer.files)
      }
    },
    [handleFileSelect],
  )

  const handleSend = useCallback(() => {
    if (disabled || (!message.trim() && files.length === 0)) return
    if (files.some((f) => f.uploadStatus === "uploading")) {
      alert("Please wait for files to finish uploading.")
      return
    }
    onSendMessage(message, files)
    setMessage("")
    setFiles([])
    files.forEach((file) => {
      if (file.preview) URL.revokeObjectURL(file.preview)
    })
    if (textareaRef.current) textareaRef.current.style.height = "auto"
  }, [message, files, disabled, onSendMessage])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  const hasContent = message.trim() || files.length > 0
  const canSend = hasContent && !disabled && !files.some((f) => f.uploadStatus === "uploading")

  return (
    <div
      className={cn(
        "relative bg-white border border-gray-300 rounded-xl shadow-lg transition-all duration-300",
        isDragging && "border-blue-500 ring-4 ring-blue-500/20",
      )}
      onDragEnter={(e) => handleDragEvent(e, true)}
      onDragOver={(e) => handleDragEvent(e, true)}
      onDragLeave={(e) => handleDragEvent(e, false)}
      onDrop={handleDrop}
    >
      {isDragging && (
        <div className="absolute inset-0 z-10 bg-blue-50 border-2 border-dashed border-blue-400 rounded-xl flex flex-col items-center justify-center pointer-events-none">
          <ImageIcon className="h-8 w-8 text-blue-500" />
          <p className="mt-2 text-sm font-semibold text-blue-600">Drop files to attach</p>
        </div>
      )}
      <div className="p-2">
        {files.length > 0 && (
          <div className="px-2 pt-2 pb-3 border-b border-gray-200">
            <div className="flex gap-3 overflow-x-auto">
              {files.map((file) => (
                <FilePreviewCard key={file.id} file={file} onRemove={removeFile} />
              ))}
            </div>
          </div>
        )}
        <div className="flex items-end gap-2 p-2">
          <Button
            size="icon"
            variant="ghost"
            className="h-10 w-10 flex-shrink-0 text-gray-500 hover:text-blue-600"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || files.length >= maxFiles}
            title="Attach files"
          >
            <Plus className="h-5 w-5" />
          </Button>
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            className="flex-1 max-h-[120px] resize-none border-0 bg-transparent shadow-none focus-visible:ring-0 text-base"
            rows={1}
          />
          <Button
            size="icon"
            className={cn(
              "h-10 w-10 flex-shrink-0 rounded-full transition-colors",
              canSend ? "bg-blue-600 hover:bg-blue-700 text-white" : "bg-gray-200 text-gray-400 cursor-not-allowed",
            )}
            onClick={handleSend}
            disabled={!canSend}
            title="Send message"
          >
            <ArrowUp className="h-5 w-5" />
          </Button>
        </div>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={(e) => {
          handleFileSelect(e.target.files)
          if (e.target) e.target.value = ""
        }}
      />
    </div>
  )
}
