#!/usr/bin/env python3
"""
Deep Researcher - Main entry point
A flexible research tool that can scrape the web and analyze information using LLMs.
"""

import argparse
import logging
import os
import sys
from datetime import datetime

from researcher.deep_researcher import DeepResearcher
from researcher.config import Config


def setup_logging(debug_mode=False):
    """Set up logging configuration"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"deep_researcher_{timestamp}.log")
    
    log_level = logging.DEBUG if debug_mode else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger("deep_researcher")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Deep Researcher - Web research and content generation tool"
    )
    
    parser.add_argument(
        "--mode", "-m",
        choices=["comedy", "research"],
        default="research",
        help="Operation mode: 'comedy' for late night show script, 'research' for general research"
    )
    
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Research query or topic"
    )
    
    parser.add_argument(
        "--articles", "-a",
        type=int,
        default=3,
        help="Number of articles to analyze per topic (default: 3)"
    )
    
    parser.add_argument(
        "--ollama-url",
        type=str,
        default="http://localhost:11434",
        help="Ollama API URL (default: http://localhost:11434)"
    )
    
    parser.add_argument(
        "--ollama-model",
        type=str,
        default="mistral",
        help="Ollama model to use for basic tasks (default: mistral)"
    )
    
    parser.add_argument(
        "--reasoning-model",
        type=str,
        default="deepseek-r1",
        help="Ollama model to use for advanced reasoning tasks (default: deepseek-r1)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directory to store output files (default: output)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with additional logging"
    )
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Enable content validation mode to verify extraction"
    )
    
    return parser.parse_args()


def main():
    """Main function to run the Deep Researcher tool"""
    # Parse command line arguments 
    args = parse_arguments()
    
    # Now we can safely use args.debug
    logger = setup_logging(args.debug)
    logger.info("Starting Deep Researcher")
    
    if args.debug:
        logger.info("Debug mode enabled")
    
    if args.validate:
        logger.info("Content validation mode enabled")
    
    # Set up configuration
    config = Config(
        ollama_url=args.ollama_url,
        ollama_model=args.ollama_model,
        reasoning_model=args.reasoning_model,
        output_dir=args.output_dir
    )
    
    try:
        # Initialize and run the researcher
        researcher = DeepResearcher(config)
        
        if args.mode == "comedy":
            logger.info("Running in comedy mode - generating late night show script")
            result = researcher.generate_comedy_script()
            print("\n\n========== LATE NIGHT SHOW SCRIPT ==========\n")
            print(result)
            print("\n========== END OF SCRIPT ==========\n")
            
        elif args.mode == "research":
            if not args.query:
                raise ValueError("Research mode requires a query (--query)")
                
            logger.info(f"Running in research mode - researching: {args.query}")
            result = researcher.research_and_summarize(args.query, max_articles=args.articles, validate_content=args.validate)
            print("\n\n========== RESEARCH SUMMARY ==========\n")
            print(result)
            print("\n========== END OF SUMMARY ==========\n")
            
        logger.info(f"All outputs saved to the '{args.output_dir}' directory")
        
    except Exception as e:
        logger.error(f"Error running Deep Researcher: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1
    
    finally:
        # Clean up resources
        try:
            if 'researcher' in locals():
                researcher.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
