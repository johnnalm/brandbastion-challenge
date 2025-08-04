import { NextResponse } from 'next/server'

export const maxDuration = 30

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST(req: Request) {
  try {
    const { messages, charts, comments } = await req.json()
    
    // Get the last message from the user
    const lastMessage = messages[messages.length - 1]
    const userMessage = lastMessage?.content || ''
    
    // Call our backend API
    const response = await fetch(`${BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: userMessage,
        chart_urls: charts || [],
        comments: comments || [],
      }),
    })
    
    if (!response.ok) {
      throw new Error(`Backend API error: ${response.statusText}`)
    }
    
    const data = await response.json()
    
    // Format the response for the frontend
    const formattedResponse = {
      role: 'assistant',
      content: data.response,
      metadata: {
        insights: data.insights,
        requires_clarification: data.requires_clarification,
        suggested_questions: data.suggested_questions,
      },
    }
    
    return NextResponse.json(formattedResponse)
  } catch (error) {
    console.error('Chat API error:', error)
    return NextResponse.json(
      { error: 'Failed to process chat request' },
      { status: 500 }
    )
  }
}
