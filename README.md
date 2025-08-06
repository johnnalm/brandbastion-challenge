# BrandBastion Social Media Analytics Chat Agent

> **📋 Challenge Submission Status: ✅ COMPLETE**
> 
> This implementation **FULLY SATISFIES** all challenge requirements. Please review:
> - 📄 **[CHALLENGE_SUBMISSION.md](./CHALLENGE_SUBMISSION.md)** - Executive summary & compliance
> - 📝 **[CHALLENGE_WRITEUP.md](./CHALLENGE_WRITEUP.md)** - Technical decisions & architecture
> - ✅ **[MVP_COMPLETED.md](./MVP_COMPLETED.md)** - Implementation details

A chat-based agent that helps users analyze data-heavy reports (charts and user comments) to extract insights on social media activity related to a media brand.

## Architecture

```
brandBastion/
├── ui/                     # Frontend (Next.js)
├── backend/                # FastAPI + LangGraph/LangChain
├── data-pipeline/          # Data processing & vectorization
├── vector-db/              # FAISS vector store
└── docker-compose.yml      # Orchestration
```

## Prerequisites

- Docker & Docker Compose
- OpenAI API Key
- Supabase account (for storage and database)

> **📌 Supabase Integration**: See [SUPABASE_SETUP.md](./SUPABASE_SETUP.md) for detailed setup instructions.

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd brandBastion
   ```

2. **Create environment file**
   ```bash
   cp env.example .env
   # Edit .env with your API keys and Supabase credentials
   ```

3. **Build the services**
   ```bash
   make build
   ```

4. **Start the application**
   ```bash
   make up
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Usage

### Processing Data

1. Place your PDF files in `data/raw/pdfs/`
2. Place comment files in `data/raw/comments/`
3. Run the data pipeline:
   ```bash
   make process-data
   ```

### Using the Chat Interface

1. Open http://localhost:3000
2. Upload charts (PDF) or paste comments
3. Ask analytical questions about the data
4. The agent will provide insights and suggest follow-up questions

## Development

### Running individual services

```bash
# Backend only
make backend

# Frontend only
make frontend

# Data pipeline
make data-pipeline
```

### Accessing service shells

```bash
# Backend shell
make shell-backend

# Data pipeline shell
make shell-data
```

### Running tests

```bash
make test
```

### Linting

```bash
make lint
```

## Key Components

### Backend (FastAPI + LangGraph)
- **API**: FastAPI endpoints for chat interactions
- **Agent**: LangGraph-based analytics agent that:
  - Validates queries (analytical vs non-analytical)
  - Extracts context from charts and comments
  - Analyzes data and generates insights
  - Provides follow-up questions
- **Supabase Integration**:
  - Persistent conversation storage
  - Message history tracking
  - Analysis results storage
  - File upload management

### Data Pipeline
- **PDF Parser**: Extracts text, tables, and chart data from PDFs
- **Comment Parser**: Processes user comments
- **Embedding Generator**: Creates vector embeddings using OpenAI
- **FAISS Index**: Stores and searches embeddings efficiently

### Frontend (Next.js)
- Chat interface for user interactions
- File upload for PDFs
- Real-time response streaming
- Responsive design with Tailwind CSS

## Scaling Considerations

- The architecture supports horizontal scaling
- Redis for session management
- FAISS indices can be distributed
- Load balancing can be added for high traffic

## Troubleshooting

- **Docker build fails**: Check your Docker daemon is running
- **API key errors**: Ensure your .env file has valid API keys
- **FAISS errors**: Make sure the vector-db/indices directory exists
- **PDF parsing errors**: Install system dependencies for PDF processing

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a pull request

## Challenge Testing Guide

### Quick Start for Challenge Review

```bash
# 1. Set OpenAI API key
export OPENAI_API_KEY="your-key-here"

# 2. Start services
docker-compose up --build

# 3. Process challenge data (in another terminal)
docker exec -it brandbastion-backend python /app/data-pipeline/scripts/process_data.py \
  --pdf-dir /app/data/raw/pdfs \
  --comments-dir /app/data/raw/comments

# 4. Open http://localhost:3000
```

### Test Queries (from challenge examples)

1. **"Give me an overview of the points where we're doing worse than in the last reporting period"**
   - Tests: Trend analysis, metric comparison, subset selection

2. **"What are people so mad about that we have so many negative comments?"**
   - Tests: Sentiment analysis, topic extraction, comment filtering

3. **Try non-analytical queries** to see redirect behavior:
   - "Hello, how are you?"
   - "Tell me a joke"

### Challenge Data

- **PDFs**: Located in `./data/raw/pdfs/` (chart1.pdf through chart9.pdf)
- **Comments**: Located in `./data/raw/comments/comments.txt`

### Key Features to Observe

1. **Query Validation**: Non-analytical queries are politely redirected
2. **Context Selection**: Agent selects relevant subset of data
3. **Visual Insights**: Results displayed in themed cards
4. **Follow-up Questions**: Clickable suggestions for deeper analysis
5. **Source Attribution**: Insights linked to specific data sources