"""
Browser module for Deep Researcher - Fixed version to properly extract external links
Handles browser setup, navigation, content extraction, and search result browsing
"""

import logging
import time
import base64
import os
import re
from io import BytesIO
from typing import Dict, List, Optional, Tuple, Union

from PIL import Image, ImageDraw
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

from researcher.config import Config


class Browser:
    """Browser class for web navigation and content extraction"""
    
    def __init__(self, config: Config):
        """Initialize the browser with configuration settings
        
        Args:
            config: Configuration settings
        """
        self.config = config
        self.driver = None
        self.logger = logging.getLogger("deep_researcher.browser")
        self.setup_browser()
    
    def setup_browser(self) -> None:
        """Set up and configure the Chrome browser with anti-detection measures"""
        # Browser setup code remains the same
        # ...
        chrome_options = Options()
        
        # Anti-detection options
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(f"--user-agent={self.config.user_agent}")
        
        # Standard options
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        
        # Performance options
        chrome_options.add_argument("--page-load-strategy=eager")
        chrome_options.page_load_strategy = 'eager'
        
        # Use headless mode if configured
        if self.config.headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
        
        try:
            # Additional options to avoid detection
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            
            # Initialize the driver
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Set timeouts
            self.driver.set_page_load_timeout(self.config.page_load_timeout)
            self.driver.set_script_timeout(self.config.script_timeout)
            
            # Execute CDP commands to prevent detection
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
                """
            })
            
            # Set user agent override
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": self.config.user_agent
            })
            self.driver.execute_cdp_cmd('Network.enable', {})
            
            # Navigate to a blank page to initialize the browser
            self.driver.get("about:blank")
            time.sleep(1)
            self.logger.info("Browser setup completed successfully with anti-detection measures")
            
        except WebDriverException as e:
            self.logger.error(f"Error setting up browser: {e}")
            self.logger.info("Attempting fallback browser setup")
            
            try:
                # Fallback with more conservative options
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument(f"--user-agent={self.config.user_agent}")
                chrome_options.page_load_strategy = 'eager'
                
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.set_page_load_timeout(self.config.page_load_timeout)
                self.driver.set_script_timeout(self.config.script_timeout)
                self.driver.get("about:blank")
                self.logger.info("Browser setup completed with fallback options")
                
            except WebDriverException as e2:
                self.logger.critical(f"Critical error setting up browser: {e2}")
                raise RuntimeError(f"Failed to initialize browser: {e2}")
    

    def find_links(self, css_selectors: list = None, timeout: int = 15, filter_blocked: bool = True) -> list:
        """Find external links on the search results page
        
        Args:
            css_selectors: CSS selectors to find links
            timeout: Timeout for finding links
            filter_blocked: Whether to filter out links from blocked sites
            
        Returns:
            list: List of direct URL strings (not WebElement objects)
        """
        if not self.driver:
            self.logger.error("Browser not initialized")
            return []
        
        # Specific selectors for DuckDuckGo search results
        if css_selectors is None:
            css_selectors = [
                ".result__title a", 
                ".result__a", 
                ".result--web a", 
                "article a",
                ".c-base a",
                ".web-result a",
                ".react-results--main .tilegroup__link",
                ".react-results--main a[href]"
            ]
        
        direct_urls = []
        start_time = time.time()
        self.logger.info("Searching for external result links")
        
        # First approach: use direct JavaScript to extract all external links
        try:
            external_urls = self.driver.execute_script("""
                // Find all result links that don't point to duckduckgo
                const links = Array.from(document.querySelectorAll('a[href]'))
                    .filter(a => {
                        const href = a.getAttribute('href');
                        return href && 
                            !href.includes('duckduckgo.com') && 
                            !href.startsWith('javascript:') &&
                            !href.startsWith('#') &&
                            a.textContent && 
                            a.textContent.trim().length > 5;
                    });
                    
                // Return an array of {url, text} objects
                return links.map(a => ({
                    url: a.href,
                    text: a.textContent.trim()
                }));
            """)
            
            if external_urls and len(external_urls) > 0:
                self.logger.info(f"Found {len(external_urls)} external URLs via JavaScript")
                
                # Filter and process the extracted URLs
                for item in external_urls:
                    url = item.get('url', '')
                    text = item.get('text', 'Untitled')
                    
                    # Skip internal DDG links and blocked sites
                    if not url or 'duckduckgo.com' in url.lower():
                        continue
                        
                    if filter_blocked and any(blocked_site in url.lower() for blocked_site in self.config.blocked_sites):
                        continue
                    
                    # Add to our list
                    direct_urls.append((url, text))
        
        except Exception as e:
            self.logger.error(f"Error executing JavaScript to find external URLs: {e}")
        
        # If we found enough links, return them
        if len(direct_urls) >= 3:
            self.logger.info(f"Extracted {len(direct_urls)} valid external URLs via JavaScript")
            return direct_urls
        
        # Fallback approach: try each CSS selector
        for selector in css_selectors:
            if time.time() - start_time > timeout:
                self.logger.warning("Link finding timeout reached")
                break
                
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                if elements:
                    for link in elements:
                        try:
                            url = link.get_attribute('href')
                            text = link.text.strip() if link.text else "Untitled"
                            
                            # Skip internal DDG links, empty links and blocked sites
                            if not url or 'duckduckgo.com' in url.lower() or url.startswith('javascript:') or url.startswith('#'):
                                continue
                                
                            if filter_blocked and any(blocked_site in url.lower() for blocked_site in self.config.blocked_sites):
                                continue
                            
                            # Check if this URL is already in our list
                            if not any(existing_url == url for existing_url, _ in direct_urls):
                                direct_urls.append((url, text))
                        except Exception as link_error:
                            self.logger.debug(f"Error processing link: {link_error}")
                            continue
                    
                    self.logger.info(f"Found {len(direct_urls)} total links after checking selector '{selector}'")
                    
                    if len(direct_urls) >= 5:  # If we have enough links, stop searching
                        break
            except Exception as e:
                self.logger.debug(f"Error finding links with selector {selector}: {e}")
                continue
        
        # Last resort: get all <a> tags in a simpler way
        if len(direct_urls) < 3 and time.time() - start_time <= timeout:
            try:
                self.logger.info("Using fallback method to get all <a> tags")
                all_links = self.driver.find_elements(By.TAG_NAME, "a")
                
                for link in all_links:
                    try:
                        url = link.get_attribute('href')
                        text = link.text.strip() if link.text else "Untitled"
                        
                        # Apply same filtering logic
                        if not url or 'duckduckgo.com' in url.lower() or url.startswith('javascript:') or url.startswith('#') or len(text) < 5:
                            continue
                            
                        if filter_blocked and any(blocked_site in url.lower() for blocked_site in self.config.blocked_sites):
                            continue
                        
                        # Check for duplicates
                        if not any(existing_url == url for existing_url, _ in direct_urls):
                            direct_urls.append((url, text))
                    except Exception:
                        continue
                    
                    # Limit to a reasonable number
                    if len(direct_urls) >= 10:
                        break
                        
                self.logger.info(f"Final fallback found {len(direct_urls)} external URLs")
                
            except Exception as e:
                self.logger.error(f"Error in fallback link finding: {e}")
        
        self.logger.info(f"Total extracted: {len(direct_urls)} valid external URLs")
        # Log a few examples
        for i, (url, text) in enumerate(direct_urls[:3]):
            self.logger.info(f"Sample URL {i+1}: {text[:30]} -> {url}")
                
        return direct_urls
 
    def browse_and_analyze_results(self, query: str, max_articles: int = 3, search_type: str = "web", 
                            max_timeout: int = 45, save_dir: Optional[str] = None) -> List[Dict]:
        """
        Browse search results, visit pages, and analyze content
        
        Args:
            query: Search query
            max_articles: Maximum number of articles to visit
            search_type: Type of search ("web" or "news")
            max_timeout: Maximum timeout for the entire operation
            save_dir: Directory to save extracted content and screenshots
            
        Returns:
            List[Dict]: Extracted information from visited articles
        """
        self.logger.info(f"Starting to browse and analyze results for query: {query}")
        
        # Search for the query
        if not self.search_duckduckgo(query, search_type):
            self.logger.error(f"Failed to search for {query}")
            return []
        
        # Take screenshot of search results
        search_screenshot = self.take_screenshot()
        if save_dir:
            from researcher.utils import save_screenshot
            os.makedirs(save_dir, exist_ok=True)
            screenshot_path = os.path.join(save_dir, "search_results.png")
            save_screenshot(search_screenshot, screenshot_path)
            self.logger.info(f"Saved search results screenshot to {screenshot_path}")
        
        # Get direct URLs instead of WebElement objects
        direct_urls = self.find_links(filter_blocked=True)
        if not direct_urls:
            self.logger.warning(f"No suitable links found for query: {query}")
            return []
        
        # Log the number of links found
        self.logger.info(f"Found {len(direct_urls)} links for query: {query}")
        
        # Visit and analyze articles
        article_info = []
        visited_count = 0
        
        # Visit each valid URL up to max_articles
        for i, (url, title) in enumerate(direct_urls[:max_articles+3]):
            if visited_count >= max_articles:
                break
                
            self.logger.info(f"Visiting article {i+1}: {title[:50]} at {url}")
            
            # Create article-specific files if save_dir is provided
            if save_dir:
                from researcher.utils import clean_filename
                article_filename_base = f"article_{i+1}_{clean_filename(title)[:30]}"
                article_content_path = os.path.join(save_dir, f"{article_filename_base}.txt")
                article_screenshot_path = os.path.join(save_dir, f"{article_filename_base}.png")
            
            # Open article in new tab
            if not self.open_new_tab(url):
                self.logger.warning(f"Failed to open article in new tab: {url}")
                continue
            
            try:
                # Wait for page to load
                wait_time = min(15, max_timeout / 3)
                WebDriverWait(self.driver, wait_time).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(2)  # Additional wait for dynamic content
                
                # Take a screenshot of the article
                article_screenshot = self.take_screenshot()
                if save_dir:
                    from researcher.utils import save_screenshot
                    save_screenshot(article_screenshot, article_screenshot_path)
                    self.logger.info(f"Saved article screenshot to {article_screenshot_path}")
                
                # Extract content from the article
                article_text, metadata = self.extract_content()
                
                # Save full article text to file if save_dir is provided
                if save_dir and article_text:
                    with open(article_content_path, "w", encoding="utf-8") as f:
                        f.write(article_text)
                    self.logger.info(f"Saved article content to {article_content_path}")
                
                # If we found text, add it to the results
                if article_text and len(article_text) > 200:
                    # Add metadata for the article
                    article_metadata = {
                        'url': url,
                        'title': title,
                        **metadata
                    }
                    
                    # Add to collected information
                    article_info.append({
                        'title': title,
                        'url': url,
                        'content': article_text,
                        'metadata': article_metadata,
                        'screenshot': article_screenshot if save_dir is None else None
                    })
                    
                    self.logger.info(f"Successfully extracted {len(article_text)} characters from article: {title[:40]}")
                    visited_count += 1
                else:
                    self.logger.warning(f"No substantial content extracted from: {url}")
                
            except TimeoutException:
                self.logger.warning(f"Timeout waiting for article to load: {url}")
            except Exception as e:
                self.logger.error(f"Error processing article {url}: {e}")
            finally:
                # Always close the tab and switch back to search results
                self.close_current_tab()
        
        self.logger.info(f"Completed browsing and analyzing {visited_count} articles for query: {query}")
        return article_info

    def navigate(self, url: str, timeout: int = None) -> bool:
        """Navigate to a URL with timeout handling
        
        Args:
            url: URL to navigate to
            timeout: Custom timeout in seconds (uses config default if None)
            
        Returns:
            bool: True if navigation was successful, False otherwise
        """
        if not self.driver:
            self.logger.error("Browser not initialized")
            return False
        
        if timeout is None:
            timeout = self.config.page_load_timeout
        
        self.logger.info(f"Navigating to {url}")
        start_time = time.time()
        
        try:
            # Set timeouts for this navigation
            self.driver.set_page_load_timeout(timeout)
            self.driver.set_script_timeout(timeout)
            
            # Navigate to the URL
            self.driver.get(url)
            
            # Wait for the body element to be present
            WebDriverWait(self.driver, min(10, timeout)).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Additional wait for dynamic content
            time.sleep(min(5, timeout / 3))
            
            elapsed = time.time() - start_time
            self.logger.info(f"Successfully navigated to {url} in {elapsed:.2f}s")
            return True
            
        except TimeoutException:
            elapsed = time.time() - start_time
            self.logger.warning(f"Timeout after {elapsed:.2f}s while navigating to {url}")
            return False
            
        except WebDriverException as e:
            elapsed = time.time() - start_time
            self.logger.error(f"Error after {elapsed:.2f}s navigating to {url}: {e}")
            return False

    def search_duckduckgo(self, query: str, search_type: str = "web", timeout: int = 45) -> bool:
        """Performs a search on DuckDuckGo
        
        Args:
            query: Search query
            search_type: Type of search ("web" or "news")
            timeout: Maximum time to wait for search results
            
        Returns:
            bool: True if search was successful, False otherwise
        """
        self.logger.info(f"Searching DuckDuckGo for: {query} (type: {search_type})")
        
        # Format search URL based on type
        if search_type.lower() == "news":
            search_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}&t=h_&df=w&iar=news&ia=news"
        else:
            search_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}&t=h_"
        
        # Navigate to search page
        success = self.navigate(search_url, timeout)
        
        if success:
            try:
                # Wait for search results to appear with a specific timeout
                wait_time = min(15, timeout / 2)
                WebDriverWait(self.driver, wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".react-results--main, .result__body, .results"))
                )
                
                # Additional wait for dynamic content
                time.sleep(min(3, timeout / 10))
                
                self.logger.info(f"Search results loaded for query: {query}")
                return True
                
            except TimeoutException:
                self.logger.warning(f"Timeout waiting for search results for query: {query}")
                return False
                
            except Exception as e:
                self.logger.error(f"Error while waiting for search results: {e}")
                return False
        else:
            self.logger.error(f"Failed to navigate to search page for query: {query}")
            return False
    
    def take_screenshot(self) -> str:
        """Take a screenshot of the current browser window and encode as base64
        
        Returns:
            str: Base64 encoded screenshot
        """
        if not self.driver:
            self.logger.error("Browser not initialized")
            return self._create_dummy_screenshot("Browser not initialized")
        
        try:
            # Pause briefly to ensure page is rendered
            time.sleep(1)
            
            # Scroll to ensure dynamic content is loaded
            self.driver.execute_script("window.scrollTo(0, 300);")
            time.sleep(0.5)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
            
            # Get page dimensions
            total_height = self.driver.execute_script("return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
            viewport_width = self.driver.execute_script("return window.innerWidth")
            
            # Set window size to capture full page
            self.driver.set_window_size(viewport_width, min(total_height, 5000))
            time.sleep(0.5)
            
            # Take the screenshot
            screenshot = self.driver.get_screenshot_as_png()
            encoded = base64.b64encode(screenshot).decode('utf-8')
            
            # Reset window size
            self.driver.set_window_size(1920, 1080)
            
            return encoded
            
        except Exception as e:
            self.logger.error(f"Error taking screenshot: {e}")
            
            # Attempt a simpler screenshot approach
            try:
                screenshot = self.driver.get_screenshot_as_png()
                return base64.b64encode(screenshot).decode('utf-8')
                
            except Exception:
                return self._create_dummy_screenshot("Screenshot Failed")
    
    def _create_dummy_screenshot(self, message: str) -> str:
        """Create a dummy screenshot with an error message
        
        Args:
            message: Error message to display
            
        Returns:
            str: Base64 encoded dummy screenshot
        """
        self.logger.warning(f"Creating dummy screenshot with message: {message}")
        img = Image.new('RGB', (800, 600), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((100, 300), message, fill=(0, 0, 0))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def extract_content(self, timeout: int = 30) -> Tuple[str, Dict[str, str]]:
        """Extract content from the current page using multiple methods
        
        Args:
            timeout: Timeout for content extraction
            
        Returns:
            Tuple[str, Dict[str, str]]: Extracted text and metadata
        """
        if not self.driver:
            self.logger.error("Browser not initialized")
            return "Browser not initialized", {}
        
        metadata = {
            "url": self.driver.current_url,
            "title": self.driver.title,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        start_time = time.time()
        
        # Try multiple methods to extract content
        content = self._extract_with_js()
        
        # If first method didn't work well, try selectors
        if not content or len(content) < 200:
            content = self._extract_with_selectors()
            
        # If still no good content, try paragraphs
        if not content or len(content) < 200:
            content = self._extract_from_paragraphs()
        
        # Final fallback
        if not content or len(content) < 200:
            try:
                content = self.driver.find_element(By.TAG_NAME, "body").text
            except Exception as e:
                self.logger.error(f"Error getting body text: {e}")
                content = "Failed to extract content."
        
        # Clean up the content
        content = self._clean_content(content)
        
        elapsed = time.time() - start_time
        metadata["extraction_time"] = f"{elapsed:.2f}s"
        metadata["content_length"] = str(len(content))
        
        self.logger.info(f"Extracted {len(content)} characters in {elapsed:.2f}s")
        return content, metadata
    
    def _extract_with_js(self) -> str:
        """Extract content using JavaScript
        
        Returns:
            str: Extracted content
        """
        try:
            return self.driver.execute_script("""
                // Get the body text
                var bodyText = document.body.innerText;
                
                // Try to remove common navigation, header, footer text
                var elements = document.querySelectorAll('nav, header, footer, .nav, .menu, .cookie, .ad, .advertisement, #comments, .comments');
                for(var i=0; i < elements.length; i++) {
                    if(elements[i] && elements[i].innerText) {
                        bodyText = bodyText.replace(elements[i].innerText, '');
                    }
                }
                
                return bodyText;
            """)
        except Exception as e:
            self.logger.error(f"Error extracting content with JS: {e}")
            return ""
    
    def _extract_with_selectors(self) -> str:
        """Extract content using common content selectors
        
        Returns:
            str: Extracted content
        """
        content = ""
        selectors = [
            "article", 
            ".article-content", 
            ".article-body", 
            ".content", 
            "main",
            ".post-content"
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    content = elements[0].text
                    self.logger.info(f"Content extracted using selector: {selector}")
                    if len(content) > 200:
                        break
            except Exception:
                continue
        
        return content
    
    def _extract_from_paragraphs(self) -> str:
        """Extract content from paragraph elements
        
        Returns:
            str: Extracted content
        """
        try:
            paragraphs = self.driver.find_elements(By.TAG_NAME, "p")
            paragraph_texts = [p.text for p in paragraphs if p.text and len(p.text) > 40]
            content = "\n\n".join(paragraph_texts)
            self.logger.info(f"Content extracted from {len(paragraph_texts)} paragraphs")
            return content
        except Exception as e:
            self.logger.error(f"Error extracting from paragraphs: {e}")
            return ""
    
    def _clean_content(self, content: str) -> str:
        """Clean the extracted content
        
        Args:
            content: Raw extracted content
            
        Returns:
            str: Cleaned content
        """
        if not content:
            return ""
            
        # Remove excess whitespace
        content = content.strip()
        content = content.replace("\t", " ")
        content = content.replace("\r", "\n")
        
        # Remove multiple consecutive newlines
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = re.sub(r'(\n\n)\1+', '\n\n', content)
        
        return content
    
    def open_new_tab(self, url: str) -> bool:
        """Open a URL in a new tab
        
        Args:
            url: URL to open
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.driver:
            self.logger.error("Browser not initialized")
            return False
        
        try:
            # Get current number of windows
            original_window = self.driver.current_window_handle
            
            # Open new tab
            self.driver.execute_script(f"window.open('{url}', '_blank');")
            time.sleep(1)
            
            # Switch to the new tab
            self.driver.switch_to.window(self.driver.window_handles[-1])
            return True
            
        except Exception as e:
            self.logger.error(f"Error opening new tab: {e}")
            return False
    
    def close_current_tab(self) -> bool:
        """Close the current tab and switch back to the first tab
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.driver:
            self.logger.error("Browser not initialized")
            return False
        
        try:
            # Close current tab if we have more than one
            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
                time.sleep(1)
                return True
            else:
                self.logger.warning("Only one tab open, cannot close")
                return False
                
        except Exception as e:
            self.logger.error(f"Error closing tab: {e}")
            return False
    
    def cleanup(self) -> None:
        """Close the browser and clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Browser closed successfully")
            except Exception as e:
                self.logger.error(f"Error closing browser: {e}")
            
            self.driver = None
