"""
Advanced analytics utilities for the Analytics Agent
"""
import re
from typing import List, Dict, Any, Tuple, Optional
from collections import Counter
import numpy as np
from textblob import TextBlob
import spacy

# Load spaCy model for advanced NLP (fallback to basic if not available)
try:
    nlp = spacy.load("en_core_web_sm")
except:
    nlp = None

class MetricsExtractor:
    """Extract numerical metrics and statistics from text"""
    
    def __init__(self):
        # Patterns for different types of metrics
        self.patterns = {
            'percentage': r'(\d+(?:\.\d+)?)\s*%',
            'currency': r'\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
            'number_with_label': r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*([A-Za-z]+)',
            'comparison': r'(?:increased?|decreased?|grew|fell|rose|dropped)\s*(?:by\s*)?(\d+(?:\.\d+)?)\s*%?',
            'multiplier': r'(\d+(?:\.\d+)?)[xX]\s*(?:more|higher|greater|less|lower)',
            'range': r'(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)',
            'time_period': r'(?:daily|weekly|monthly|quarterly|yearly|annual)',
            'growth_rate': r'growth\s*(?:rate)?\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*%?'
        }
    
    def extract_metrics(self, text: str) -> Dict[str, List[Any]]:
        """Extract all types of metrics from text"""
        metrics = {
            'percentages': [],
            'currency_values': [],
            'raw_numbers': [],
            'comparisons': [],
            'trends': [],
            'time_periods': []
        }
        
        # Extract percentages
        percentages = re.findall(self.patterns['percentage'], text)
        metrics['percentages'] = [float(p) for p in percentages]
        
        # Extract currency values
        currency = re.findall(self.patterns['currency'], text)
        metrics['currency_values'] = [float(c.replace(',', '')) for c in currency]
        
        # Extract comparisons (increases/decreases)
        comparisons = re.findall(self.patterns['comparison'], text, re.IGNORECASE)
        for comp in comparisons:
            metrics['comparisons'].append({
                'value': float(comp),
                'context': self._get_context(text, comp)
            })
        
        # Extract trends
        metrics['trends'] = self._extract_trends(text)
        
        # Extract time periods
        time_periods = re.findall(self.patterns['time_period'], text, re.IGNORECASE)
        metrics['time_periods'] = list(set(time_periods))
        
        # Extract multipliers (3x, 2.5x, etc.)
        multipliers = re.findall(self.patterns['multiplier'], text)
        metrics['multipliers'] = [float(m) for m in multipliers]
        
        return metrics
    
    def _extract_trends(self, text: str) -> List[Dict[str, Any]]:
        """Extract trend information"""
        trends = []
        trend_words = {
            'positive': ['increase', 'growth', 'rise', 'improve', 'gain', 'up'],
            'negative': ['decrease', 'decline', 'fall', 'drop', 'loss', 'down']
        }
        
        for direction, words in trend_words.items():
            for word in words:
                if word in text.lower():
                    context = self._get_context(text, word)
                    trends.append({
                        'direction': direction,
                        'indicator': word,
                        'context': context
                    })
        
        return trends
    
    def _get_context(self, text: str, term: str, window: int = 50) -> str:
        """Get surrounding context for a term"""
        try:
            index = text.lower().find(str(term).lower())
            if index == -1:
                return ""
            start = max(0, index - window)
            end = min(len(text), index + len(str(term)) + window)
            return text[start:end].strip()
        except:
            return ""
    
    def calculate_statistics(self, numbers: List[float]) -> Dict[str, float]:
        """Calculate basic statistics for a list of numbers"""
        if not numbers:
            return {}
        
        return {
            'mean': np.mean(numbers),
            'median': np.median(numbers),
            'std': np.std(numbers),
            'min': min(numbers),
            'max': max(numbers),
            'range': max(numbers) - min(numbers)
        }


class SentimentAnalyzer:
    """Analyze sentiment in comments and text"""
    
    def __init__(self):
        self.positive_words = {
            'excellent', 'amazing', 'love', 'great', 'wonderful', 'fantastic',
            'awesome', 'perfect', 'best', 'outstanding', 'brilliant', 'superb'
        }
        self.negative_words = {
            'terrible', 'awful', 'hate', 'bad', 'horrible', 'worst', 'poor',
            'disappointing', 'useless', 'waste', 'annoying', 'frustrating'
        }
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment using TextBlob and custom rules"""
        # Use TextBlob for basic sentiment
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 to 1
        subjectivity = blob.sentiment.subjectivity  # 0 to 1
        
        # Custom sentiment scoring
        words = text.lower().split()
        positive_count = sum(1 for word in words if word in self.positive_words)
        negative_count = sum(1 for word in words if word in self.negative_words)
        
        # Determine overall sentiment
        if polarity > 0.1:
            sentiment_label = 'positive'
        elif polarity < -0.1:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'neutral'
        
        # Check for strong sentiment
        if positive_count >= 2 or polarity > 0.5:
            sentiment_label = 'very_positive'
        elif negative_count >= 2 or polarity < -0.5:
            sentiment_label = 'very_negative'
        
        return {
            'polarity': polarity,
            'subjectivity': subjectivity,
            'sentiment': sentiment_label,
            'positive_words': positive_count,
            'negative_words': negative_count,
            'confidence': abs(polarity) * (1 - subjectivity/2)
        }
    
    def analyze_batch(self, texts: List[str]) -> Dict[str, Any]:
        """Analyze sentiment for multiple texts"""
        results = []
        for text in texts:
            results.append(self.analyze_sentiment(text))
        
        # Aggregate results
        avg_polarity = np.mean([r['polarity'] for r in results])
        sentiment_distribution = Counter([r['sentiment'] for r in results])
        
        return {
            'individual_results': results,
            'average_polarity': avg_polarity,
            'sentiment_distribution': dict(sentiment_distribution),
            'overall_sentiment': self._get_overall_sentiment(avg_polarity),
            'positive_ratio': sentiment_distribution.get('positive', 0) / len(results) if results else 0
        }
    
    def _get_overall_sentiment(self, avg_polarity: float) -> str:
        """Determine overall sentiment from average polarity"""
        if avg_polarity > 0.3:
            return 'predominantly_positive'
        elif avg_polarity < -0.3:
            return 'predominantly_negative'
        else:
            return 'mixed'


class TrendDetector:
    """Detect patterns and trends in data"""
    
    def detect_temporal_patterns(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect temporal patterns in time-series data"""
        patterns = {
            'peak_times': [],
            'low_times': [],
            'trends': [],
            'seasonality': None
        }
        
        # Extract time-based patterns from text mentions
        time_patterns = {
            'morning': r'(?:morning|[0-9]{1,2}\s*am|early)',
            'afternoon': r'(?:afternoon|[0-9]{1,2}\s*pm|midday)',
            'evening': r'(?:evening|night|late)',
            'weekday': r'(?:monday|tuesday|wednesday|thursday|friday|weekday)',
            'weekend': r'(?:saturday|sunday|weekend)'
        }
        
        return patterns
    
    def identify_key_topics(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Identify key topics and themes"""
        if not texts:
            return []
        
        # Simple keyword extraction
        all_text = ' '.join(texts).lower()
        words = re.findall(r'\b\w+\b', all_text)
        
        # Filter out common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
        filtered_words = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Count frequencies
        word_freq = Counter(filtered_words)
        
        # Get top topics
        topics = []
        for word, count in word_freq.most_common(10):
            topics.append({
                'topic': word,
                'frequency': count,
                'percentage': (count / len(filtered_words)) * 100 if filtered_words else 0
            })
        
        return topics
    
    def detect_anomalies(self, metrics: List[float]) -> List[Dict[str, Any]]:
        """Detect anomalies in numerical data"""
        if len(metrics) < 3:
            return []
        
        anomalies = []
        mean = np.mean(metrics)
        std = np.std(metrics)
        
        # Simple z-score based anomaly detection
        for i, value in enumerate(metrics):
            z_score = (value - mean) / std if std > 0 else 0
            if abs(z_score) > 2:  # More than 2 standard deviations
                anomalies.append({
                    'index': i,
                    'value': value,
                    'z_score': z_score,
                    'severity': 'high' if abs(z_score) > 3 else 'medium'
                })
        
        return anomalies


class InsightGenerator:
    """Generate actionable insights from analyzed data"""
    
    def __init__(self):
        self.metrics_extractor = MetricsExtractor()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.trend_detector = TrendDetector()
    
    def generate_insights(self, context_sources: List[Dict[str, Any]]) -> List[str]:
        """Generate insights from context sources"""
        insights = []
        
        # Separate charts and comments
        chart_sources = [s for s in context_sources if s.get('source_type') == 'chart']
        comment_sources = [s for s in context_sources if s.get('source_type') == 'comment']
        
        # Analyze charts for metrics
        if chart_sources:
            chart_insights = self._analyze_chart_metrics(chart_sources)
            insights.extend(chart_insights)
        
        # Analyze comments for sentiment
        if comment_sources:
            comment_insights = self._analyze_comment_sentiment(comment_sources)
            insights.extend(comment_insights)
        
        # Cross-analysis insights
        if chart_sources and comment_sources:
            cross_insights = self._generate_cross_insights(chart_sources, comment_sources)
            insights.extend(cross_insights)
        
        return insights[:10]  # Return top 10 insights
    
    def _analyze_chart_metrics(self, chart_sources: List[Dict[str, Any]]) -> List[str]:
        """Analyze metrics from chart data"""
        insights = []
        all_metrics = []
        
        for source in chart_sources:
            text = source.get('content', '')
            metrics = self.metrics_extractor.extract_metrics(text)
            
            # Generate insights from percentages
            if metrics['percentages']:
                avg_percentage = np.mean(metrics['percentages'])
                insights.append(f"Average percentage metric: {avg_percentage:.1f}%")
                
                if any(p > 50 for p in metrics['percentages']):
                    insights.append("Significant metrics above 50% detected, indicating strong performance")
            
            # Analyze trends
            if metrics['trends']:
                positive_trends = sum(1 for t in metrics['trends'] if t['direction'] == 'positive')
                negative_trends = sum(1 for t in metrics['trends'] if t['direction'] == 'negative')
                
                if positive_trends > negative_trends:
                    insights.append(f"Predominantly positive trends ({positive_trends} positive vs {negative_trends} negative)")
                elif negative_trends > positive_trends:
                    insights.append(f"Areas of concern: {negative_trends} negative trends identified")
            
            all_metrics.extend(metrics['percentages'])
        
        # Statistical insights
        if all_metrics:
            stats = self.metrics_extractor.calculate_statistics(all_metrics)
            if stats['range'] > 20:
                insights.append(f"High variance in metrics (range: {stats['range']:.1f}%), suggesting diverse performance areas")
        
        return insights
    
    def _analyze_comment_sentiment(self, comment_sources: List[Dict[str, Any]]) -> List[str]:
        """Analyze sentiment from comments"""
        insights = []
        comments = [s.get('content', '') for s in comment_sources]
        
        if comments:
            sentiment_results = self.sentiment_analyzer.analyze_batch(comments)
            
            # Overall sentiment insight
            overall = sentiment_results['overall_sentiment']
            insights.append(f"Overall user sentiment is {overall.replace('_', ' ')}")
            
            # Positive ratio insight
            pos_ratio = sentiment_results['positive_ratio']
            if pos_ratio > 0.7:
                insights.append(f"Strong positive feedback: {pos_ratio*100:.0f}% of comments are positive")
            elif pos_ratio < 0.3:
                insights.append(f"Significant negative feedback: {(1-pos_ratio)*100:.0f}% of comments express concerns")
            
            # Topic analysis
            topics = self.trend_detector.identify_key_topics(comments)
            if topics:
                top_topics = ', '.join([t['topic'] for t in topics[:3]])
                insights.append(f"Key discussion topics: {top_topics}")
        
        return insights
    
    def _generate_cross_insights(self, chart_sources: List[Dict[str, Any]], 
                                comment_sources: List[Dict[str, Any]]) -> List[str]:
        """Generate insights by cross-referencing charts and comments"""
        insights = []
        
        # Extract metrics from charts
        chart_metrics = []
        for source in chart_sources:
            metrics = self.metrics_extractor.extract_metrics(source.get('content', ''))
            if metrics['percentages']:
                chart_metrics.extend(metrics['percentages'])
        
        # Get sentiment from comments
        comments = [s.get('content', '') for s in comment_sources]
        sentiment_results = self.sentiment_analyzer.analyze_batch(comments)
        
        # Cross-reference insights
        if chart_metrics and sentiment_results['average_polarity'] > 0:
            avg_metric = np.mean(chart_metrics)
            if avg_metric > 10 and sentiment_results['positive_ratio'] > 0.6:
                insights.append("Positive metrics align with positive user sentiment, indicating successful performance")
            elif avg_metric < 5 and sentiment_results['positive_ratio'] < 0.4:
                insights.append("Low metrics correlate with negative sentiment, requiring immediate attention")
        
        return insights