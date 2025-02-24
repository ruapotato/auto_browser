"""
LLM client module for Deep Researcher
Handles interactions with Ollama LLM API
"""

import logging
import time
from typing import Dict, Optional, Union

import requests

from researcher.config import Config


class LLMClient:
    """Client for interacting with Ollama LLM API"""
    
    def __init__(self, config: Config):
        """Initialize the LLM client
        
        Args:
            config: Configuration settings
        """
        self.config = config
        self.logger = logging.getLogger("deep_researcher.llm")
        self.reasoning_model = "deepseek-r1"  # Advanced model for reasoning tasks
        self.basic_model = config.ollama_model  # Default model for basic tasks
    
    def query(
        self, 
        prompt: str, 
        model: Optional[str] = None, 
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        timeout: int = 60,
        use_reasoning: bool = False
    ) -> str:
        """Query the LLM with a prompt
        
        Args:
            prompt: The prompt to send to the LLM
            model: Model to use (falls back to config if None)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            system_prompt: Optional system prompt
            timeout: Request timeout in seconds
            use_reasoning: Whether to use the advanced reasoning model
            
        Returns:
            str: LLM response
        """
        if not prompt:
            self.logger.warning("Empty prompt provided")
            return ""
        
        # Select appropriate model based on task complexity
        if model is None:
            if use_reasoning:
                model = self.reasoning_model
                self.logger.info(f"Using advanced reasoning model: {model}")
            else:
                model = self.basic_model
        
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "temperature": temperature
        }
        
        # Add optional parameters if provided
        if max_tokens is not None:
            data["max_tokens"] = max_tokens
            
        if system_prompt is not None:
            data["system"] = system_prompt
        
        start_time = time.time()
        self.logger.info(f"Querying {model} with prompt of length {len(prompt)} chars")
        
        try:
            response = requests.post(
                f"{self.config.ollama_url}/api/generate",
                json=data,
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json().get("response", "")
                elapsed = time.time() - start_time
                self.logger.info(
                    f"Received response of length {len(result)} chars in {elapsed:.2f}s"
                )
                return result
            else:
                self.logger.error(
                    f"Error from LLM API: {response.status_code} - {response.text}"
                )
                return f"Error: API returned status code {response.status_code}"
                
        except requests.RequestException as e:
            elapsed = time.time() - start_time
            self.logger.error(f"Request error after {elapsed:.2f}s: {e}")
            return f"Error: Failed to connect to LLM API ({e})"
            
        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.error(f"Unexpected error after {elapsed:.2f}s: {e}")
            return f"Error: {e}"
    
    def extract_trends(self, content: str) -> list:
        """Extract trends from content using LLM
        
        Args:
            content: Content to analyze
            
        Returns:
            list: Extracted trends
        """
        prompt = f"""
        You are helping to extract trending topics from Google Trends page content.
        Identify the top trending searches from the provided text.
        For each trend, provide the search term and search volume if available.
        
        Format your response as a structured list of JSON objects:
        [
          {{
            "rank": 1,
            "title": "Trending Topic Name",
            "volume": "xxx searches" (if available, otherwise "Unknown")
          }},
          ...
        ]
        
        Include only the JSON array, nothing else.
        
        Here's the content:
        {content[:8000]}  # Limit to first 8000 chars
        """
        
        response = self.query(
            prompt=prompt,
            system_prompt="You extract structured data from text. Respond with valid JSON only.",
            temperature=0.3
        )
        
        import json
        import re
        
        # Try to extract JSON from the response
        try:
            # Find anything that looks like a JSON array
            json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
            if json_match:
                response = json_match.group(0)
            
            extracted_data = json.loads(response)
            return extracted_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from LLM response: {e}")
            # Try to create a basic structure from the response
            return self._fallback_trend_extraction(response)
    
    def _fallback_trend_extraction(self, text: str) -> list:
        """Fallback method to extract trends from text
        
        Args:
            text: Raw text from LLM
            
        Returns:
            list: Extracted trends
        """
        import re
        
        trends = []
        # Look for numbered lists or patterns that resemble rankings
        lines = text.split('\n')
        
        rank = 1
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
                
            # Look for patterns like "1. Topic name" or "#1 Topic name"
            match = re.search(r'(?:^|\s)(\d+)[\.:\)]\s+(.+?)(?:\s+-\s+|:\s+|$)', line)
            if match:
                extracted_rank = int(match.group(1))
                title = match.group(2).strip()
                
                # Look for volume information
                volume_match = re.search(r'(\d+[Kk]?(?:\+|\s+)(?:searches|views|results))', line)
                volume = volume_match.group(1) if volume_match else "Unknown"
                
                trends.append({
                    "rank": extracted_rank,
                    "title": title,
                    "volume": volume
                })
                rank = extracted_rank + 1
            else:
                # If we can't find a proper format, use sequential numbering
                title = line.strip()
                if len(title) > 5 and not title.startswith(('Summary', 'Note:', 'These are')):
                    trends.append({
                        "rank": rank,
                        "title": title,
                        "volume": "Unknown"
                    })
                    rank += 1
        
        # Return up to 10 trends
        return trends[:10]
    
    def summarize_content(self, content: str, topic: str, metadata: Dict[str, str] = None, use_reasoning: bool = False) -> str:
        """Summarize content on a specific topic
        
        Args:
            content: Content to summarize
            topic: Topic being researched
            metadata: Metadata about the content (URL, title, etc.)
            use_reasoning: Whether to use the advanced reasoning model
            
        Returns:
            str: Summarized content
        """
        if not metadata:
            metadata = {}
        
        # Truncate content if too long
        content_for_llm = content
        if len(content) > 8000:
            # Take the first 6000 chars and last 2000 for context
            content_for_llm = content[:6000] + "\n\n[...]\n\n" + content[-2000:]
        
        # Standard prompt for all topics
        prompt = f"""
        Summarize the following article about '{topic}' in a concise paragraph.
        Focus on key facts, developments, and relevance.
        Ignore any advertisements, navigation elements, or unrelated content.
        
        ARTICLE TITLE: {metadata.get('title', 'Untitled')}
        SOURCE URL: {metadata.get('url', 'Unknown')}
        
        ARTICLE TEXT:
        {content_for_llm}
        
        SUMMARY:
        """
        
        # First summarize with mistral for basic tasks
        if use_reasoning:
            # For complex queries related to AI/LLMs, use the mistral model first for summarization
            basic_summary = self.query(
                prompt=prompt,
                system_prompt="You are a technical summarizer extracting key information.",
                temperature=0.3,
                use_reasoning=False  # Use the basic model
            )
            
            # Then use the reasoning model for deeper analysis 
            enhanced_prompt = f"""
            Now think deeply about the following content that has been summarized from an article about '{topic}'. 
            Extract specific technical details, model names, benchmarks, and key performance metrics.
            
            ARTICLE SUMMARY: {basic_summary}
            
            DETAILED TECHNICAL ANALYSIS:
            """
            
            return self.query(
                prompt=enhanced_prompt,
                system_prompt="You are a technical AI expert who precisely analyzes information with a focus on specific details and technical accuracy.",
                temperature=0.3,
                use_reasoning=True
            )
        else:
            # Standard prompt for simpler topics
            return self.query(
                prompt=prompt,
                system_prompt="You are a precise summarizer who extracts the most relevant information.",
                temperature=0.3
            )
    
    def create_research_report(self, topic: str, summaries: list, metadata: Dict[str, str] = None) -> str:
        """Create a comprehensive research report from multiple summaries
        
        Args:
            topic: Topic being researched
            summaries: List of article summaries
            metadata: Additional metadata
            
        Returns:
            str: Research report
        """
        if not metadata:
            metadata = {}
        
        # Format summaries for the prompt
        formatted_summaries = ""
        for i, summary in enumerate(summaries):
            formatted_summaries += f"SOURCE {i+1}: {summary.get('title', 'Untitled')}\n"
            formatted_summaries += f"URL: {summary.get('url', 'Unknown')}\n"
            formatted_summaries += f"SUMMARY: {summary.get('summary', '')}\n\n"
        
        # Identify if this is a query about AI models or reasoning capabilities
        is_ai_related = any(term in topic.lower() for term in 
                           ["llm", "language model", "ai model", "neural network", 
                            "deep learning", "machine learning", "artificial intelligence",
                            "thinking", "reasoning", "gpt", "llama", "mistral", "deepseek"])
        
        # Create a more targeted prompt for AI-related queries
        if is_ai_related:
            # First create a basic synthesis using the regular model
            self.logger.info("Creating initial summary with basic model for AI-related topic")
            basic_prompt = f"""
            Synthesize the key information from these sources about "{topic}":
            
            {formatted_summaries}
            
            Highlight the most important facts, figures, and findings.
            """
            
            initial_synthesis = self.query(
                prompt=basic_prompt,
                system_prompt="You extract and synthesize key information from multiple sources.",
                temperature=0.3,
                use_reasoning=False
            )
            
            # Then use the reasoning model for more detailed analysis
            self.logger.info("Using advanced reasoning model for final AI-related report")
            advanced_prompt = f"""
            Create a comprehensive, detailed research report about "{topic}" based on this synthesized information:
            
            {initial_synthesis}
            
            IMPORTANT: If the query is about the "best" models or technologies:
            1. Provide specific, concrete rankings or comparisons rather than general statements
            2. Include the latest cutting-edge models like DeepSeek-V3, LLaMA 3.1 405B, and Mixtral 8x22B
            3. Mention key metrics like parameter count, context window size, and benchmark performance
            4. Discuss licensing and accessibility considerations
            5. Address specific capabilities like reasoning, programming, and mathematical problem-solving
            
            Your report should:
            1. Start with a nuanced introduction explaining what makes a model "best" depends on requirements
            2. Evaluate the main points plus your knowledge of state-of-the-art models
            3. End with specific recommendations based on different use cases
            
            FORMAT:
            - Use clear headings for sections
            - Present a balanced, thorough analysis with concrete details
            
            RESEARCH REPORT:
            """
            
            return self.query(
                prompt=advanced_prompt,
                system_prompt="You are an AI research expert who creates balanced, comprehensive reports with specific technical details and up-to-date knowledge about state-of-the-art models.",
                max_tokens=3072,
                temperature=0.3,
                use_reasoning=True
            )
        else:
            # Standard prompt for other topics
            prompt = f"""
            Create a comprehensive research report about "{topic}" based on the following sources.
            
            SOURCES:
            {formatted_summaries}
            
            Your report should:
            1. Start with a brief introduction to the topic
            2. Synthesize the main points from all sources
            3. Note any contradictions or differing perspectives between sources
            4. Include specific facts, figures, and quotes when relevant
            5. End with a conclusion that summarizes key insights
            
            FORMAT:
            - Use clear headings for sections
            - Organize information logically
            - Include citations to specific sources when appropriate
            
            RESEARCH REPORT:
            """
            
            return self.query(
                prompt=prompt,
                system_prompt="You are a thorough researcher who creates balanced, comprehensive reports.",
                max_tokens=2048,
                temperature=0.5,
                use_reasoning=False
            )
    
    def create_comedy_summary(self, topic: str, research: str) -> str:
        """Create a comedic late-night style summary
        
        Args:
            topic: Topic to create comedy about
            research: Research information
            
        Returns:
            str: Comedic summary
        """
        prompt = f"""
        You are a late-night comedy show writer. Create a brief, funny joke or monologue bit about this trending topic.
        Be witty, topical, and slightly irreverent - similar to popular late-night hosts.
        Keep it to 2-3 sentences maximum. Make it punchy and audience-ready.
        
        Use the research information to make the joke current and topical.
        Reference specific details from the research if possible.
        
        Trending topic: {topic}
        Research information: {research[:2000]}
        
        Your late-night joke:
        """
        
        return self.query(
            prompt=prompt,
            system_prompt="You are a comedy writer for a late-night TV show.",
            temperature=0.8
        )
    
    def generate_daily_facts(self) -> str:
        """Generate interesting facts about the current day
        
        Returns:
            str: Interesting facts
        """
        from datetime import datetime
        
        today = datetime.now().strftime("%B %d, %Y")
        prompt = f"""
        Generate 3 interesting and surprising facts about today ({today}).
        These should be real facts about historical events, celebrity birthdays, or unusual holidays.
        Make them somewhat obscure but verifiable, and word them in an engaging way.
        """
        
        return self.query(
            prompt=prompt,
            system_prompt="You provide accurate historical facts about specific dates.",
            temperature=0.7
        )
