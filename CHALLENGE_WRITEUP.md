# BrandBastion Analytics Challenge - Technical Writeup

## 1. Architecture Decisions

### Context Storage Decision: FAISS Vector Database

**Why FAISS:**
- **Semantic Search**: Unlike keyword matching, FAISS enables semantic similarity search, crucial for understanding user queries that may not use exact terminology from the charts/comments
- **Scalability**: FAISS handles millions of vectors efficiently with sub-linear search time
- **Flexibility**: Can add/update indices on-the-fly without rebuilding entire database
- **Memory Efficiency**: Supports various index types (IVF, HNSW) for memory/speed tradeoffs

**Implementation:**
```python
# Context stored as embeddings with metadata
context_sources = [
    {
        "content": "actual text",
        "metadata": {"source": "chart", "page": 1},
        "similarity_score": 0.87,
        "source_type": "chart"
    }
]
```

### Agent Decision Graph: LangGraph State Machine

**Architecture:**
```
Start → Validate Query → [Analytical?]
                          ├─ Yes → Extract Context → Analyze Data → Generate Response → End
                          └─ No → Redirect to Analytical → End
```

**Why LangGraph:**
- **Explicit State Management**: Clear state transitions prevent conversation drift
- **Modular Nodes**: Each step (validate, extract, analyze) is independently testable
- **Conditional Routing**: Built-in support for branching logic
- **Type Safety**: TypedDict states ensure data consistency

### Tool vs LLM Responsibility Split

**Custom Tools (Deterministic):**
- **MetricsExtractor**: Regex-based extraction for accuracy (percentages, currency, trends)
- **SentimentAnalyzer**: TextBlob + rule-based for consistent scoring
- **TrendDetector**: Statistical analysis for anomaly detection
- **FAISS Search**: Vector similarity for relevant context selection

**LLM Responsibilities:**
- Query understanding and classification
- Natural language response generation
- Contextual insight synthesis
- Follow-up question generation

**Rationale**: Deterministic tools ensure reliable metric extraction and prevent hallucination of numbers. LLM handles language understanding and generation where creativity is beneficial.

## 2. Handling Scale

### 2 Million Comments Database

**Approach:**
1. **Hierarchical Indexing**:
   ```python
   # Multiple FAISS indices by time/category
   indices = {
       "comments_2024_q1": faiss_index_1,
       "comments_2024_q2": faiss_index_2,
       "comments_by_sentiment": faiss_index_3
   }
   ```

2. **Preprocessing Pipeline**:
   - Batch processing with Apache Spark/Dask
   - Pre-compute embeddings during off-peak hours
   - Store in distributed FAISS indices (sharded by date/topic)

3. **Smart Sampling**:
   - Initial coarse search across index metadata
   - Fine-grained search only on relevant shards
   - Statistical sampling for aggregate metrics

### 500 Concurrent Users

**Strategy:**
1. **Caching Layer**:
   ```python
   # Redis for query/embedding cache
   cache_key = f"embed:{hash(query)}"
   if cached := redis.get(cache_key):
       return cached
   ```

2. **Load Balancing**:
   - Multiple backend instances behind nginx
   - Sticky sessions for conversation continuity
   - Read replicas for FAISS indices

3. **Async Processing**:
   - FastAPI async endpoints
   - Background job queue (Celery) for heavy analysis
   - WebSocket for real-time updates

4. **Resource Optimization**:
   - Connection pooling for LLM API calls
   - Batch embedding generation
   - Circuit breakers for external services

## 3. Cloud Architecture Deployment

### Architecture Overview
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   CloudFront    │────▶│   ALB/API GW     │────▶│  ECS Fargate    │
│      (CDN)      │     │  (Load Balancer) │     │   (Backend)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                           │
                                ┌──────────────────────────┼──────────────────┐
                                │                          │                  │
                        ┌───────▼────────┐      ┌─────────▼──────┐   ┌───────▼────────┐
                        │  Redis Cluster │      │  RDS PostgreSQL│   │  S3 + FAISS    │
                        │ (Session/Cache)│      │  (Conversations)│   │  (Embeddings)  │
                        └────────────────┘      └────────────────┘   └────────────────┘
```

### State Management
- **Session State**: Redis with TTL (conversation context)
- **Persistent State**: PostgreSQL (user history, analytics)
- **Vector State**: S3 + EFS for FAISS indices

### Latency Optimization
1. **Edge Caching**: CloudFront for static assets
2. **Regional Deployment**: Multi-region with GeoDNS
3. **Precomputed Embeddings**: Background processing
4. **Connection Pooling**: Reuse LLM API connections

### Race Conditions
```python
# Distributed locks with Redis
async def process_upload(user_id: str, file_id: str):
    lock = await redis.lock(f"upload:{user_id}:{file_id}")
    if not lock:
        return {"error": "Processing in progress"}
    
    try:
        # Process file
        await create_embeddings(file_id)
    finally:
        await lock.release()
```

### Infrastructure as Code
```yaml
# AWS CDK/Terraform for reproducible deployments
resources:
  ecs_service:
    cpu: 2048
    memory: 4096
    autoscaling:
      min: 2
      max: 50
      target_cpu: 70
```

## 4. Grounding and Hallucination Prevention

### RAG Implementation
1. **Strict Context Grounding**:
   ```python
   prompt = """
   Base your analysis ONLY on the provided context.
   Do not make up data or statistics.
   If information is insufficient, say so explicitly.
   
   Context: {verified_context}
   """
   ```

2. **Multi-Stage Validation**:
   - **Stage 1**: Deterministic metric extraction (no LLM)
   - **Stage 2**: LLM analysis with extracted metrics as constraints
   - **Stage 3**: Post-processing validation against source data

3. **Confidence Scoring**:
   ```python
   def calculate_confidence(response, context_sources):
       # Higher score for responses citing specific sources
       citations = extract_citations(response)
       coverage = len(citations) / len(context_sources)
       return min(coverage * similarity_score, 1.0)
   ```

### Hallucination Mitigation Strategies

1. **Prompt Engineering**:
   - Explicit instructions to avoid speculation
   - Examples of good vs bad responses
   - Chain-of-thought reasoning for transparency

2. **Source Attribution**:
   ```python
   # Every insight linked to source
   insight = {
       "text": "Engagement increased by 47.3%",
       "source": "chart_1.pdf:page_2:line_15",
       "confidence": 0.92
   }
   ```

3. **Fact Checking Pipeline**:
   - Regex validation for claimed metrics
   - Cross-reference with original documents
   - Flag uncertain claims for user review

4. **Model Selection**:
   - **Current**: GPT-3.5-turbo (cost-effective, sufficient for structured analysis)
   - **Ideal**: GPT-4 or Claude-3 Opus for complex reasoning
   - **Future**: Fine-tuned model on analytics-specific data

### Monitoring & Feedback
```python
# Track hallucination metrics
metrics = {
    "unsupported_claims": count_unverified_statements(),
    "source_coverage": calculate_source_usage(),
    "user_corrections": track_user_feedback()
}
```

## Conclusion

This implementation prioritizes:
- **Accuracy**: Deterministic tools for factual extraction
- **Scalability**: FAISS + caching for millions of documents
- **Reliability**: RAG + validation to prevent hallucinations
- **User Experience**: Clear insights with source attribution

The architecture is production-ready and can scale from MVP to enterprise deployment.