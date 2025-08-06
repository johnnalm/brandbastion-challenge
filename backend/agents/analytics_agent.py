from typing import TypedDict, Annotated, List, Optional, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.callbacks.base import AsyncCallbackHandler
import os
import sys
from pathlib import Path

from embeddings.generator import EmbeddingGenerator

# Import analytics utilities
from .analytics_utils import MetricsExtractor, SentimentAnalyzer, TrendDetector, InsightGenerator

# Define the state for our graph
class AgentState(TypedDict):
    query: str
    charts: Optional[List[str]]
    comments: Optional[List[str]]
    is_analytical: bool
    context: str
    context_sources: List[Dict[str, Any]]  # Store FAISS search results
    response: str
    insights: List[str]
    requires_clarification: bool
    suggested_questions: List[str]

class AnalyticsAgent:
    def __init__(self, default_model: str = "gpt-3.5-turbo"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("[ANALYTICS AGENT] OPENAI_API_KEY environment variable is not set!")
        
        print(f"[ANALYTICS AGENT] Initializing with OpenAI API key: {'*' * 10}{api_key[-4:]}")
        print(f"[ANALYTICS AGENT] Default model: {default_model}")
        
        self.default_model = default_model
        self.llm = ChatOpenAI(
            model=default_model,
            temperature=0.7,
            openai_api_key=api_key
        )
        self.embedding_generator = EmbeddingGenerator()
        self.max_context_sources = 5  # Maximum number of context sources to use
        
        # Initialize analytics tools
        self.metrics_extractor = MetricsExtractor()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.trend_detector = TrendDetector()
        self.insight_generator = InsightGenerator()
        
        self.graph = self._build_graph()
    
    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("validate_query", self.validate_query)
        workflow.add_node("extract_context", self.extract_context)
        workflow.add_node("analyze_data", self.analyze_data)
        workflow.add_node("generate_response", self.generate_response)
        workflow.add_node("redirect_to_analytical", self.redirect_to_analytical)
        
        # Add edges
        workflow.add_edge("extract_context", "analyze_data")
        workflow.add_edge("analyze_data", "generate_response")
        workflow.add_edge("generate_response", END)
        workflow.add_edge("redirect_to_analytical", END)
        
        # Add conditional edge from validate_query
        workflow.add_conditional_edges(
            "validate_query",
            lambda x: "extract_context" if x["is_analytical"] else "redirect_to_analytical",
            {
                "extract_context": "extract_context",
                "redirect_to_analytical": "redirect_to_analytical"
            }
        )
        
        # Set entry point
        workflow.set_entry_point("validate_query")
        
        return workflow.compile()
    
    def validate_query(self, state: AgentState) -> AgentState:
        """Validate if the query is analytical in nature"""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a query classifier for a social media analytics system.
            Determine if the user's query is analytical (related to data, metrics, insights, trends) 
            or non-analytical (general conversation, off-topic).
            Respond with only 'analytical' or 'non-analytical'."""),
            HumanMessage(content=state["query"])
        ])
        
        response = self.llm.invoke(prompt.format_messages())
        state["is_analytical"] = "analytical" in response.content.lower()
        return state
    
    def extract_context(self, state: AgentState) -> AgentState:
        """Extract relevant context from charts and comments using FAISS"""
        context_sources = []
        context_parts = []
        
        # Search in charts index if it exists
        try:
            if self._index_exists("charts"):
                chart_results = self.embedding_generator.search_similar(
                    index_name=self._get_actual_index_name("charts"),
                    query=state["query"],
                    k=self.max_context_sources
                )
                
                # Add chart results with ranking
                for idx, result in enumerate(chart_results):
                    result["rank"] = idx + 1
                    result["source_type"] = "chart"
                    context_sources.append(result)
                    
                    # Format for context
                    context_parts.append(
                        f"[Chart Context {idx+1}] (Score: {result['similarity_score']:.3f})\n"
                        f"Page: {result['metadata'].get('page', 'N/A')}\n"
                        f"Content: {result['content']}\n"
                    )
        except FileNotFoundError:
            if state.get("charts"):
                context_parts.append(f"Note: Charts index not found. {len(state['charts'])} charts provided but not indexed.")
        
        # Search in comments index if it exists
        try:
            if self._index_exists("comments"):
                comment_results = self.embedding_generator.search_similar(
                    index_name=self._get_actual_index_name("comments"),
                    query=state["query"],
                    k=self.max_context_sources
                )
                
                # Add comment results with ranking
                for idx, result in enumerate(comment_results):
                    result["rank"] = idx + 1
                    result["source_type"] = "comment"
                    context_sources.append(result)
                    
                    # Format for context
                    context_parts.append(
                        f"[Comment Context {idx+1}] (Score: {result['similarity_score']:.3f})\n"
                        f"Comment ID: {result['metadata'].get('comment_id', 'N/A')}\n"
                        f"Content: {result['content']}\n"
                    )
        except FileNotFoundError:
            if state.get("comments"):
                context_parts.append(f"Note: Comments index not found. {len(state['comments'])} comments provided but not indexed.")
        
        # Deduplicate results by content and comment_id
        if context_sources:
            seen_content = set()
            unique_sources = []
            unique_parts = []
            
            for source in context_sources:
                content_key = source['content'].strip()
                comment_id = source['metadata'].get('comment_id', 'unknown')
                unique_key = f"{comment_id}:{content_key[:50]}"
                
                if unique_key not in seen_content:
                    seen_content.add(unique_key)
                    unique_sources.append(source)
            
            # Sort by similarity score and limit results
            unique_sources.sort(key=lambda x: x['similarity_score'], reverse=True)
            unique_sources = unique_sources[:self.max_context_sources]
            
            # Rebuild context_parts with unique results
            for idx, source in enumerate(unique_sources):
                source["rank"] = idx + 1
                source_type = source.get("source_type", "unknown")
                if source_type == "comment":
                    unique_parts.append(
                        f"[Comment Context {idx+1}] (Score: {source['similarity_score']:.3f})\n"
                        f"Comment ID: {source['metadata'].get('comment_id', 'N/A')}\n"
                        f"Content: {source['content']}\n"
                    )
                else:
                    unique_parts.append(
                        f"[Chart Context {idx+1}] (Score: {source['similarity_score']:.3f})\n"
                        f"Page: {source['metadata'].get('page', 'N/A')}\n"
                        f"Content: {source['content']}\n"
                    )
            
            context_sources = unique_sources
            context_parts = unique_parts
            context_parts.insert(0, f"Found {len(context_sources)} unique context sources for query: '{state['query']}'\n")
        else:
            context_parts.append("No indexed data found. Please ensure data is processed and indexed first.")
        
        state["context"] = "\n".join(context_parts)
        state["context_sources"] = context_sources
        return state
    
    def _get_actual_index_name(self, logical_name: str) -> str:
        """Map logical index names to actual index names"""
        index_mapping = {
            "charts": "brandbastion",
            "comments": "brandbastion_comments"
        }
        return index_mapping.get(logical_name, logical_name)
    
    def _index_exists(self, index_name: str) -> bool:
        """Check if a FAISS index exists"""
        index_path = Path(os.getenv("FAISS_INDEX_PATH", "/app/vector-db/indices"))
        actual_index_name = self._get_actual_index_name(index_name)
        index_dir = index_path / actual_index_name
        
        # Check if the index directory exists and contains required files
        if index_dir.exists():
            index_file = index_dir / "index.faiss"
            pkl_file = index_dir / "index.pkl"
            return index_file.exists() and pkl_file.exists()
        
        return False
    
    def analyze_data(self, state: AgentState) -> AgentState:
        """Analyze the data and extract insights using advanced analytics"""
        insights = []
        
        # Use the insight generator for comprehensive analysis
        if state["context_sources"]:
            generated_insights = self.insight_generator.generate_insights(state["context_sources"])
            insights.extend(generated_insights)
        
        # If we have specific data, do targeted analysis
        chart_sources = [s for s in state["context_sources"] if s.get('source_type') == 'chart']
        comment_sources = [s for s in state["context_sources"] if s.get('source_type') == 'comment']
        
        # Extract metrics from charts
        if chart_sources:
            all_metrics = []
            for source in chart_sources:
                metrics = self.metrics_extractor.extract_metrics(source.get('content', ''))
                
                # Add specific metric insights
                if metrics['percentages']:
                    for pct in metrics['percentages'][:3]:  # Top 3 percentages
                        insights.append(f"Key metric: {pct}% identified in data")
                
                if metrics['trends']:
                    trend_summary = self._summarize_trends(metrics['trends'])
                    if trend_summary:
                        insights.append(trend_summary)
                
                all_metrics.extend(metrics.get('percentages', []))
            
            # Statistical analysis
            if all_metrics:
                stats = self.metrics_extractor.calculate_statistics(all_metrics)
                insights.append(f"Metrics range from {stats['min']:.1f}% to {stats['max']:.1f}% (avg: {stats['mean']:.1f}%)")
        
        # Sentiment analysis for comments
        if comment_sources:
            comments = [s.get('content', '') for s in comment_sources]
            sentiment_results = self.sentiment_analyzer.analyze_batch(comments)
            
            # Add sentiment insights
            sentiment_dist = sentiment_results['sentiment_distribution']
            total_comments = len(comments)
            
            for sentiment, count in sentiment_dist.items():
                percentage = (count / total_comments) * 100
                if percentage > 20:  # Only report significant sentiments
                    insights.append(f"{sentiment.replace('_', ' ').capitalize()} sentiment in {percentage:.0f}% of comments")
            
            # Topic analysis
            topics = self.trend_detector.identify_key_topics(comments)
            if topics:
                top_3_topics = [t['topic'] for t in topics[:3]]
                insights.append(f"Most discussed topics: {', '.join(top_3_topics)}")
        
        # Use LLM for additional context-aware insights
        if state["context"] and len(insights) < 5:
            llm_insights = self._get_llm_insights(state)
            insights.extend(llm_insights)
        
        # Remove duplicates and limit to top insights
        unique_insights = []
        seen = set()
        for insight in insights:
            insight_lower = insight.lower()
            if insight_lower not in seen:
                seen.add(insight_lower)
                unique_insights.append(insight)
        
        state["insights"] = unique_insights[:8]  # Increased to 8 insights
        
        return state
    
    def _summarize_trends(self, trends: List[Dict[str, Any]]) -> str:
        """Summarize trend information"""
        if not trends:
            return ""
        
        positive = sum(1 for t in trends if t['direction'] == 'positive')
        negative = sum(1 for t in trends if t['direction'] == 'negative')
        
        if positive > negative:
            return f"Positive trend detected: {positive} growth indicators found"
        elif negative > positive:
            return f"Declining trend: {negative} decrease indicators identified"
        else:
            return "Mixed trends observed in the data"
    
    def _get_llm_insights(self, state: AgentState) -> List[str]:
        """Get additional insights from LLM"""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""Extract 2-3 specific, data-driven insights from the context.
            Focus on actionable findings and avoid generic statements."""),
            HumanMessage(content=f"Query: {state['query']}\nContext: {state['context'][:500]}")
        ])
        
        response = self.llm.invoke(prompt.format_messages())
        
        # Parse LLM insights
        insights = []
        for line in response.content.split('\n'):
            line = line.strip()
            if line and len(line) > 20:  # Only substantial insights
                insights.append(line.lstrip('-•* '))
        
        return insights[:3]
    
    def _summarize_context_sources(self, context_sources: List[Dict[str, Any]]) -> str:
        """Create a summary of context sources"""
        if not context_sources:
            return "No context sources available"
        
        chart_count = sum(1 for s in context_sources if s.get('source_type') == 'chart')
        comment_count = sum(1 for s in context_sources if s.get('source_type') == 'comment')
        
        summary = f"Total sources: {len(context_sources)}\n"
        if chart_count > 0:
            summary += f"- Chart data: {chart_count} relevant sections\n"
        if comment_count > 0:
            summary += f"- User comments: {comment_count} relevant comments\n"
        
        # Add score range
        scores = [s['similarity_score'] for s in context_sources]
        if scores:
            summary += f"- Relevance scores: {min(scores):.3f} - {max(scores):.3f}\n"
        
        return summary
    
    def generate_response(self, state: AgentState) -> AgentState:
        """Generate the final response"""
        # Generate response based on insights
        if state["insights"]:
            insights_text = "\n".join([f"• {insight}" for insight in state["insights"]])
            state["response"] = f"Based on your query about '{state['query']}', here are the key insights:\n\n{insights_text}"
        else:
            state["response"] = f"I couldn't find specific insights for your query about '{state['query']}'. Please ensure the data has been properly indexed."
        
        # Generate follow-up questions based on context
        state["suggested_questions"] = self._generate_follow_up_questions(state)
        
        # Check if clarification is needed
        state["requires_clarification"] = len(state["context_sources"]) == 0
        
        return state
    
    def _generate_follow_up_questions(self, state: AgentState) -> List[str]:
        """Generate relevant follow-up questions based on the context"""
        questions = []
        
        # If no context sources available, suggest uploading data
        if not state["context_sources"]:
            questions = [
                "Would you like me to analyze your social media data? Please upload PDFs or paste comments.",
                "Can you provide specific metrics or comments you'd like me to analyze?",
                "What type of social media insights are you looking for?"
            ]
            return questions[:3]
        
        # If we have chart data, suggest chart-related questions
        has_charts = any(s.get('source_type') == 'chart' for s in state["context_sources"])
        has_comments = any(s.get('source_type') == 'comment' for s in state["context_sources"])
        
        if has_charts:
            questions.extend([
                "Would you like to see the trend analysis over different time periods?",
                "Can I break down these metrics by specific categories?",
                "What specific metric would you like to explore in more detail?"
            ])
        
        # If we have comment data, suggest sentiment-related questions  
        if has_comments:
            questions.extend([
                "Would you like a detailed sentiment analysis of the user comments?",
                "Should I identify the main themes and topics in user feedback?",
                "Can I analyze the reasons behind negative comments?"
            ])
        
        # If we have insights, suggest deeper analysis
        if state.get("insights"):
            questions.extend([
                "Would you like me to provide actionable recommendations based on these insights?",
                "Can I compare these metrics with industry benchmarks?",
                "Should I analyze the correlation between different metrics?"
            ])
        
        # Generic analytical questions if needed
        if len(questions) < 3:
            questions.extend([
                "What specific aspect of the data would you like to explore further?",
                "Would you like to see a different perspective on this data?",
                "Can I help you identify opportunities for improvement?"
            ])
        
        # Return top 3 most relevant questions
        return questions[:3]
    
    def redirect_to_analytical(self, state: AgentState) -> AgentState:
        """Redirect non-analytical queries"""
        state["response"] = "I'm designed to help with social media analytics. Please ask questions about metrics, trends, or data insights."
        state["requires_clarification"] = True
        state["suggested_questions"] = [
            "What's the engagement rate for our latest campaign?",
            "How has our follower growth changed this month?",
            "Which content types perform best?"
        ]
        return state
    
    def create_indices_from_data(self, charts: Optional[List[str]] = None, comments: Optional[List[str]] = None) -> Dict[str, bool]:
        """Create FAISS indices from provided data"""
        results = {"charts": False, "comments": False}
        
        # Process and index charts if provided
        if charts:
            try:
                # Create simple text representations of charts
                chart_texts = []
                chart_metadatas = []
                
                for idx, chart in enumerate(charts):
                    chart_texts.append(chart)
                    chart_metadatas.append({
                        "source": "uploaded_chart",
                        "page": idx + 1,
                        "chart_id": f"chart_{idx}"
                    })
                
                # Create index
                if chart_texts:
                    self.embedding_generator.add_to_existing_index(
                        index_name=self._get_actual_index_name("charts"),
                        texts=chart_texts,
                        metadatas=chart_metadatas
                    )
                    results["charts"] = True
            except Exception as e:
                print(f"Error indexing charts: {e}")
        
        # Process and index comments if provided
        if comments:
            try:
                comment_texts = []
                comment_metadatas = []
                
                for idx, comment in enumerate(comments):
                    comment_texts.append(comment)
                    comment_metadatas.append({
                        "source": "user_comment",
                        "comment_id": f"comment_{idx}",
                        "index": idx
                    })
                
                # Create index
                if comment_texts:
                    self.embedding_generator.add_to_existing_index(
                        index_name=self._get_actual_index_name("comments"),
                        texts=comment_texts,
                        metadatas=comment_metadatas
                    )
                    results["comments"] = True
            except Exception as e:
                print(f"Error indexing comments: {e}")
        
        return results
    
    def run(self, query: str, charts: Optional[List[str]] = None, comments: Optional[List[str]] = None) -> dict:
        """Run the agent with the given inputs"""
        print(f"[ANALYTICS AGENT] Starting run with query: {query}")
        print(f"[ANALYTICS AGENT] Charts provided: {len(charts) if charts else 0}")
        print(f"[ANALYTICS AGENT] Comments provided: {len(comments) if comments else 0}")
        
        initial_state = {
            "query": query,
            "charts": charts,
            "comments": comments,
            "is_analytical": False,
            "context": "",
            "context_sources": [],
            "response": "",
            "insights": [],
            "requires_clarification": False,
            "suggested_questions": []
        }
        
        try:
            print(f"[ANALYTICS AGENT] Invoking graph...")
            result = self.graph.invoke(initial_state)
            print(f"[ANALYTICS AGENT] Graph invocation complete")
            print(f"[ANALYTICS AGENT] Response: {result.get('response', 'NO RESPONSE')[:100]}...")
            return result
        except Exception as e:
            print(f"[ANALYTICS AGENT ERROR] Error during graph invocation: {e}")
            import traceback
            print(f"[ANALYTICS AGENT ERROR] Traceback:\n{traceback.format_exc()}")
            raise
    
    async def arun_with_streaming(self, query: str, charts: Optional[List[str]] = None, 
                                   comments: Optional[List[str]] = None, 
                                   callback_handler: Optional[AsyncCallbackHandler] = None,
                                   model: Optional[str] = None) -> dict:
        """Run the agent asynchronously with streaming support"""
        print(f"[ANALYTICS AGENT] Starting async run with streaming for query: {query}")
        
        # Use provided model or fall back to default
        model_to_use = model or self.default_model
        print(f"[ANALYTICS AGENT] Using model: {model_to_use}")
        
        # Create a streaming-enabled LLM instance with callback
        if callback_handler:
            streaming_llm = ChatOpenAI(
                model=model_to_use,
                temperature=0.7,
                streaming=True,
                callbacks=[callback_handler],
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
        else:
            streaming_llm = self.llm
        
        # Prepare the state
        initial_state = {
            "query": query,
            "charts": charts,
            "comments": comments,
            "is_analytical": False,
            "context": "",
            "context_sources": [],
            "response": "",
            "insights": [],
            "requires_clarification": False,
            "suggested_questions": []
        }
        
        try:
            # Run the validation and context extraction steps
            state = self.validate_query(initial_state)
            
            if state["is_analytical"]:
                state = self.extract_context(state)
                state = await self._generate_streaming_response(state, streaming_llm)
            else:
                state = self.redirect_to_analytical(state)
            
            return state
            
        except Exception as e:
            print(f"[ANALYTICS AGENT ERROR] Error during streaming: {e}")
            import traceback
            print(f"[ANALYTICS AGENT ERROR] Traceback:\n{traceback.format_exc()}")
            raise
    
    async def _generate_streaming_response(self, state: AgentState, streaming_llm: ChatOpenAI) -> AgentState:
        """Generate streaming response using the provided LLM"""
        context = state["context"]
        query = state["query"]
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=f"""You are a social media analytics expert assistant.
            
            Context from available data:
            {context}
            
            Based on this context, provide insightful analysis answering the user's query.
            If the data doesn't contain relevant information, acknowledge this limitation.
            Focus on actionable insights, trends, and patterns in the data."""),
            HumanMessage(content=query)
        ])
        
        # Stream the response
        response_text = ""
        async for chunk in streaming_llm.astream(prompt.format_messages()):
            if chunk.content:
                response_text += chunk.content
        
        state["response"] = response_text
        
        # Generate insights after streaming is complete (non-streaming)
        if context != "No indexed data found. Please ensure data is processed and indexed first.":
            # Use context_sources instead of the incorrect parameters
            if state["context_sources"]:
                state["insights"] = self.insight_generator.generate_insights(state["context_sources"])
            else:
                # Fallback to analyze_data method for generating insights
                state = self.analyze_data(state)
        
        # Check if clarification is needed
        state["requires_clarification"] = len(state["context_sources"]) == 0 or "no indexed data" in context.lower()
        
        # Generate follow-up questions based on context
        state["suggested_questions"] = self._generate_follow_up_questions(state)
        
        return state