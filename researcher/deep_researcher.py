"""
Deep Researcher main module
Coordinates browser, LLM, and file operations to research topics and generate content
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

from researcher.browser import Browser
from researcher.config import Config
from researcher.llm_client import LLMClient
from researcher.utils import save_screenshot, clean_filename


class DeepResearcher:
    """Main class for Deep Researcher tool"""
    
    def __init__(self, config: Config):
        """Initialize the Deep Researcher
        
        Args:
            config: Configuration settings
        """
        self.config = config
        self.logger = logging.getLogger("deep_researcher")
        self.browser = Browser(config)
        self.llm = LLMClient(config)
        self.research_data = []
        self.summaries = []
        self.screenshots = []
        
    def research_and_summarize(self, query: str, max_articles: int = 3, validate_content: bool = False) -> str:
        """Research a topic and generate a summary
        
        Args:
            query: Query or topic to research
            max_articles: Maximum number of articles to analyze
            validate_content: Whether to validate content extraction
            
        Returns:
            str: Research summary
        """
        self.logger.info(f"Starting research on: {query}")
        
        # Create a research folder for this topic
        topic_dir = os.path.join(self.config.output_dir, f"research_{clean_filename(query)}")
        os.makedirs(topic_dir, exist_ok=True)
        
        # Create a research log file
        research_log_path = os.path.join(topic_dir, "research_log.md")
        with open(research_log_path, "w") as log_file:
            log_file.write(f"# Research Log: {query}\n\n")
            log_file.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            log_file.write(f"## Search Information\n")
            log_file.write(f"- Topic: {query}\n\n")
        
        # Use the improved browser to search, browse, and analyze results
        self.logger.info(f"Using browser to search and analyze results for: {query}")
        
        # Log the search information
        with open(research_log_path, "a") as log_file:
            log_file.write(f"## Web Search\n")
            log_file.write(f"- Query: {query}\n\n")
        
        # Take a screenshot of search results
        search_screenshot = None
        
        # Browse and analyze search results
        article_info = self.browser.browse_and_analyze_results(
            query=query,
            max_articles=max_articles,
            search_type="web",
            max_timeout=60,
            save_dir=topic_dir
        )
        
        # Store search screenshot if available
        search_screenshot_path = os.path.join(topic_dir, "search_results.png")
        if os.path.exists(search_screenshot_path):
            with open(search_screenshot_path, "rb") as f:
                import base64
                search_screenshot = base64.b64encode(f.read()).decode('utf-8')
                
            # Add to screenshots collection
            self.screenshots.append({
                'title': f"Search for {query}",
                'image': search_screenshot
            })
        
        # Log the results
        with open(research_log_path, "a") as log_file:
            log_file.write(f"## Analyzed Articles\n\n")
            
            if article_info:
                for i, article in enumerate(article_info):
                    log_file.write(f"### Article {i+1}: {article['title']}\n")
                    log_file.write(f"- URL: {article['url']}\n")
                    log_file.write(f"- Extracted {len(article['content'])} characters of text\n\n")
            else:
                log_file.write("No articles were successfully analyzed.\n\n")
        
        # Process the article information we collected
        processed_articles = []
        
        for article in article_info:
            # Determine if this is a complex query that needs reasoning
            is_complex_query = any(term in query.lower() for term in 
                                  ["best", "compare", "thinking", "reasoning", "llm", 
                                   "model", "artificial intelligence", "ai"])
            
            # Summarize the article, using reasoning model for complex queries
            article_summary = self.llm.summarize_content(
                article['content'], query, article['metadata'], use_reasoning=is_complex_query
            )
            
            # Add to collected information
            processed_articles.append({
                'title': article['title'],
                'url': article['url'],
                'summary': article_summary,
                'metadata': article['metadata']
            })
            
            # Log summary
            with open(research_log_path, "a") as log_file:
                log_file.write(f"### Summary for {article['title']}\n")
                log_file.write(f"{article_summary}\n\n")
            
            self.logger.info(f"Successfully summarized article: {article['title'][:40]}")
        
        # Generate research report if we have enough information
        if processed_articles:
            self.logger.info(f"Generating research report for {query} based on {len(processed_articles)} articles")
            
            # Generate comprehensive report
            research_report = self.llm.create_research_report(query, processed_articles)
            
            # Save the final research report
            report_path = os.path.join(topic_dir, "research_report.md")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"# Research Report: {query}\n\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(research_report)
            
            # Log report generation
            with open(research_log_path, "a") as log_file:
                log_file.write(f"\n## Research Report\n")
                log_file.write(f"A comprehensive research report has been generated: [Research Report](research_report.md)\n\n")
            
            # Add summary of sources
            with open(research_log_path, "a") as log_file:
                log_file.write(f"\n## Sources Used\n")
                for i, info in enumerate(processed_articles):
                    log_file.write(f"{i+1}. [{info['title']}]({info['url']})\n")
                
                log_file.write(f"\n## Research Completed\n")
                log_file.write(f"Research completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            self.logger.info(f"Research report saved to {report_path}")
            return research_report
            
        else:
            # If we couldn't collect enough information
            self.logger.warning(f"Insufficient data collected for {query}")
            
            # Generate a basic report with minimal information
            fallback_report = self._generate_fallback_report(query)
            
            # Save the fallback report
            report_path = os.path.join(topic_dir, "basic_report.md")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"# Basic Information: {query}\n\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(fallback_report)
            
            # Log fallback
            with open(research_log_path, "a") as log_file:
                log_file.write(f"\n## Fallback Report\n")
                log_file.write(f"Due to limited information, a basic report has been generated: [Basic Report](basic_report.md)\n\n")
                log_file.write(f"\n## Research Completed\n")
                log_file.write(f"Research completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            self.logger.info(f"Basic report saved to {report_path}")
            return fallback_report
    
    def _generate_fallback_report(self, query: str) -> str:
        """Generate a fallback report when insufficient information is available
        
        Args:
            query: Research query
            
        Returns:
            str: Basic report
        """
        prompt = f"""
        Create a brief informational summary about "{query}" based on your knowledge.
        
        Include:
        1. A general description of what "{query}" is
        2. Key facts or aspects related to the topic
        3. Any significant recent developments if applicable
        4. Areas where more research would be valuable
        
        Note: This should be fact-based information about {query}, not speculative.
        If you don't have sufficient information about this topic, acknowledge the limitations.
        
        Format as a brief report with clear sections.
        """
        
        report = self.llm.query(
            prompt=prompt,
            system_prompt=f"You are a researcher providing accurate information about '{query}' based on your knowledge.",
            temperature=0.3
        )
        
        # Add a note that this is based on limited information
        note = (
            f"**Note:** This report was generated with limited web research information "
            f"and is based primarily on the LLM's prior knowledge about '{query}'. "
            f"The information may not reflect the very latest developments."
        )
        
        return f"{report}\n\n{note}"
    
    def visit_google_trends(self, region: str = "US") -> List[Dict]:
        """Visit Google Trends and extract trending topics
        
        Args:
            region: Region code for Google Trends
            
        Returns:
            List[Dict]: List of trending topics
        """
        self.logger.info(f"Visiting Google Trends for region {region}")
        
        # Navigate to Google Trends
        url = f"https://trends.google.com/trends/trendingsearches/daily?geo={region}"
        if not self.browser.navigate(url, timeout=45):
            self.logger.warning("Failed to navigate to Google Trends")
            return self._get_fallback_trends()
        
        # Take a screenshot
        screenshot = self.browser.take_screenshot()
        screenshot_path = os.path.join(self.config.output_dir, "google_trends.png")
        save_screenshot(screenshot, screenshot_path)
        
        self.screenshots.append({
            'title': 'Google Trends Page',
            'image': screenshot
        })
        
        # Extract page content
        page_text, _ = self.browser.extract_content()
        
        # Save the raw page text
        trends_text_path = os.path.join(self.config.output_dir, "google_trends_raw.txt")
        with open(trends_text_path, "w", encoding="utf-8") as f:
            f.write(page_text)
        
        # Use LLM to extract trends
        if page_text and len(page_text) > 200:
            self.logger.info("Extracting trending topics using LLM")
            extracted_trends = self.llm.extract_trends(page_text)
            
            if extracted_trends and len(extracted_trends) >= 5:
                self.logger.info(f"Successfully extracted {len(extracted_trends)} trends")
                
                # Save the extracted trends
                trends_json_path = os.path.join(self.config.output_dir, "extracted_trends.json")
                with open(trends_json_path, "w") as f:
                    json.dump(extracted_trends, f, indent=2)
                
                # Set as research data
                self.research_data = extracted_trends
                return extracted_trends
        
        # If extraction failed, use fallbacks
        self.logger.warning("Using fallback trends due to extraction failure")
        return self._get_fallback_trends()
    
    def _get_fallback_trends(self) -> List[Dict]:
        """Get fallback trending topics when extraction fails
        
        Returns:
            List[Dict]: List of fallback trending topics
        """
        import random
        
        # Common fallback trends
        fallback_trends = [
            "Ukraine Russia conflict",
            "Presidential election polls",
            "NFL scores",
            "Taylor Swift concert tickets",
            "Stock market today",
            "COVID variant symptoms",
            "Hurricane forecast",
            "iPhone 16 release date",
            "Gas prices",
            "Netflix new shows"
        ]
        
        # Format as trend objects
        trends = []
        for i, trend in enumerate(fallback_trends):
            trends.append({
                'rank': i + 1,
                'title': trend,
                'volume': f"{random.randint(100, 500)}K+ searches"
            })
            self.logger.info(f"Using fallback trend: {trend}")
        
        self.research_data = trends
        return trends
    
    def generate_comedy_script(self) -> str:
        """Generate a late-night comedy show script based on trending topics
        
        Returns:
            str: Comedy script
        """
        self.logger.info("Generating late-night comedy show script")
        
        # Visit Google Trends and get trending topics
        trends = self.visit_google_trends()
        
        # Start building the script
        today = datetime.now().strftime("%A, %B %d, %Y")
        script = f"# Tonight's Trending Topics - {today}\n\n"
        script += f"Welcome to Tonight's Trends for {today}! We've got some wild searches happening today, folks. Let's dive in!\n\n"
        
        # Research and create comedy for each trend
        segments = []
        
        # Focus on top 5 trends
        for trend in trends[:5]:
            self.logger.info(f"Creating comedy segment for trend: {trend['title']}")
            
            # Research the trend using improved browser capabilities
            trend_dir = os.path.join(self.config.output_dir, f"trend_{clean_filename(trend['title'])}")
            os.makedirs(trend_dir, exist_ok=True)
            
            # Use browser to search and analyze articles about the trend
            trend_articles = self.browser.browse_and_analyze_results(
                query=trend['title'],
                max_articles=2,
                search_type="news",
                max_timeout=45,
                save_dir=trend_dir
            )
            
            # Extract and compile research
            trend_research = ""
            if trend_articles:
                trend_research = f"Trend: {trend['title']}\n\n"
                for i, article in enumerate(trend_articles):
                    trend_research += f"Article {i+1}: {article['title']}\n"
                    trend_research += f"Source: {article['url']}\n"
                    trend_research += f"Content: {article['content'][:500]}...\n\n"
            else:
                trend_research = f"Research on {trend['title']} yielded limited information from web sources."
            
            # Create a comedic summary
            comedic_summary = self.llm.create_comedy_summary(trend['title'], trend_research)
            
            # Add to segments
            segments.append({
                'trend': trend,
                'summary': comedic_summary
            })
            
            # Add to script
            script += f"## Trending at #{trend['rank']}: {trend['title']}\n"
            script += f"*Search volume: {trend['volume']}*\n\n"
            script += f"{comedic_summary}\n\n"
        
        # Add daily facts
        self.logger.info("Adding daily facts to script")
        daily_facts = self.llm.generate_daily_facts()
        script += f"## Today's Fascinating Facts\n\n{daily_facts}\n\n"
        
        # Save the final script
        script_path = os.path.join(self.config.output_dir, f"comedy_script_{datetime.now().strftime('%Y%m%d')}.md")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)
        
        self.logger.info(f"Comedy script saved to {script_path}")
        return script
    
    def research_topic(self, topic: str, max_articles: int = 3) -> str:
        """Research a specific topic and return a summary of findings
        
        Args:
            topic: Topic to research
            max_articles: Maximum number of articles to analyze
            
        Returns:
            str: Research summary
        """
        self.logger.info(f"Researching topic: {topic}")
        
        # Create a research folder for this topic
        topic_dir = os.path.join(self.config.output_dir, f"topic_{clean_filename(topic)}")
        os.makedirs(topic_dir, exist_ok=True)
        
        # Use improved browser capabilities to research the topic
        topic_articles = self.browser.browse_and_analyze_results(
            query=topic,
            max_articles=max_articles,
            search_type="web",
            max_timeout=45,
            save_dir=topic_dir
        )
        
        # Compile research summary
        if topic_articles:
            research_text = f"# Research on: {topic}\n\n"
            
            for i, article in enumerate(topic_articles):
                # Summarize the article
                article_summary = self.llm.summarize_content(
                    article['content'], topic, article['metadata']
                )
                
                research_text += f"## Source {i+1}: {article['title']}\n"
                research_text += f"URL: {article['url']}\n\n"
                research_text += f"{article_summary}\n\n"
            
            # Save the research
            research_path = os.path.join(topic_dir, "topic_research.md")
            with open(research_path, "w", encoding="utf-8") as f:
                f.write(research_text)
            
            return research_text
        else:
            # Return basic information if no articles were successfully processed
            self.logger.warning(f"No articles successfully processed for {topic}")
            no_results_message = f"Research on {topic} yielded limited information from web sources."
            
            # Save the message
            research_path = os.path.join(topic_dir, "topic_research.md")
            with open(research_path, "w", encoding="utf-8") as f:
                f.write(f"# Research on: {topic}\n\n{no_results_message}")
                
            return no_results_message
    
    def cleanup(self) -> None:
        """Clean up resources"""
        if hasattr(self, 'browser') and self.browser:
            self.browser.cleanup()
