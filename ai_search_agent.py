#!/usr/bin/env python3
"""
Microsoft Rewards Agent - AI-Powered Search Automation
Combines Microsoft Edge automation with Google's Gemini AI for intelligent search automation.
"""

import os
import sys
import time
import random
import logging
import csv
from datetime import datetime
from typing import List, Optional, Tuple
import traceback

# Third-party imports
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import TimeoutException
    from seleniumwire import webdriver as seleniumwire_webdriver  # Import seleniumwire
    from webdriver_manager.chrome import ChromeDriverManager
    
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    
    from colorama import init, Fore
    from fake_useragent import UserAgent
    from dotenv import load_dotenv
    
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    sys.exit(1)

# Initialize colorama for Windows
init(autoreset=True)

class AISearchAgent:
    """AI-powered search automation agent using Microsoft Edge and Google Gemini."""
    
    def __init__(self, config_file: str = ".env"):
        """Initialize the search agent with configuration."""
        self.load_config(config_file)
        self.setup_logging()
        self.pc_driver: Optional[seleniumwire_webdriver.Chrome] = None  # Use seleniumwire's webdriver
        self.mobile_driver: Optional[seleniumwire_webdriver.Chrome] = None
        self.ai_client = None
        self.pc_search_history: List[str] = []
        self.mobile_search_history: List[str] = []
        self.user_agent = UserAgent()
        self.session_start_time = datetime.now()
        self.proxies = self.load_proxies()  # Load proxies
        
        # Search parameters
        self.search_params = {
            "categories": [
                "technology", "current events", "pop culture", "science",
                "entertainment", "sports", "health", "travel", "food",
                "history", "nature", "space", "education", "business"
            ],
            "query_types": [
                "question", "fact", "news search", "definition",
                "how to", "what is", "why does", "comparison"
            ],
            "complexity_levels": ["simple", "detailed", "comprehensive"]
        }
        
        # Initialize components
        self._initialize_gemini()
        self._initialize_pc_browser()
        self._initialize_mobile_browser()
        self._setup_csv_logging()

    def load_config(self, config_file: str) -> None:
        """Load configuration from environment file."""
        load_dotenv(config_file)
        
        self.config = {
            'gemini_api_key': os.getenv('GEMINI_API_KEY'),
            'edge_driver_path': os.getenv('EDGE_DRIVER_PATH', 'auto'),
            'debug_mode': os.getenv('DEBUG_MODE', 'False').lower() == 'true',
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'max_cycles': int(os.getenv('MAX_SEARCH_CYCLES', '32')),
            'min_delay': int(os.getenv('MIN_DELAY', '10')),
            'max_delay': int(os.getenv('MAX_DELAY', '59')),
            'proxy': os.getenv('PROXY', None)
        }
        
        if not self.config['gemini_api_key'] or self.config['gemini_api_key'] == 'your_gemini_api_key_here':
            raise ValueError("GEMINI_API_KEY not set in .env file")

    def setup_logging(self) -> None:
        """Setup logging configuration."""
        log_level = getattr(logging, self.config['log_level'].upper())
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('search_agent.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _initialize_gemini(self) -> None:
        """Initialize Google Gemini AI client."""
        try:
            genai.configure(api_key=self.config['gemini_api_key'])
            
            # Configure safety settings
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            # Initialize the model
            self.ai_client = genai.GenerativeModel(
                model_name="gemini-2.0-flash-lite",
                safety_settings=safety_settings
            )
            
            self.logger.info(f"{Fore.GREEN}[OK] Gemini AI initialized successfully")
            
        except Exception as e:
            self.logger.error(f"{Fore.RED}[FAIL] Failed to initialize Gemini AI: {e}")
            raise

    def load_proxies(self, filename='proxies.json'):
        """Load proxies from a JSON file."""
        try:
            with open(filename, 'r') as f:
                self.proxies = json.load(f)
            self.logger.info(f"{Fore.GREEN}[OK] Loaded {len(self.proxies)} proxies")
            return self.proxies
        except Exception as e:
            self.logger.error(f"{Fore.RED}[FAIL] Failed to load proxies: {e}")
            return []

    def _initialize_pc_browser(self, proxy=None) -> None:
        """Initialize Chrome browser in PC mode with proxy support."""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1280,1024")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument(f"--user-agent={self.user_agent.desktop}")

            # Set proxy if provided
            if proxy:
                if 'username' in proxy and 'password' in proxy:
                    # Format: http://username:password@host:port
                    proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
                else:
                    # Format: http://host:port
                    proxy_url = f"http://{proxy['host']}:{proxy['port']}"
                
                self.pc_driver = seleniumwire_webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=chrome_options
                )
                self.pc_driver.proxy = proxy_url
                self.pc_driver.header_overrides = {
                    'Proxy-Authorization': f"Basic {self._encode_proxy_auth(proxy)}" if 'username' in proxy else None
                }
            else:
                self.pc_driver = seleniumwire_webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=chrome_options
                )

            self.logger.info(f"{Fore.GREEN}[OK] PC Browser initialized successfully in headless mode")

        except Exception as e:
            self.logger.error(f"{Fore.RED}[FAIL] Failed to initialize PC Browser: {e}")
            raise

    def _encode_proxy_auth(self, proxy):
        """Encode proxy authentication credentials."""
        import base64
        auth = f"{proxy['username']}:{proxy['password']}"
        return base64.b64encode(auth.encode()).decode()

    def _initialize_mobile_browser(self, proxy=None) -> None:
        """Initialize Chrome browser in Mobile mode with proxy support."""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=375,812")

            mobile_emulation = {
                "deviceMetrics": {"width": 375, "height": 812, "pixelRatio": 3.0},
                "userAgent": "Mozilla/5.0 (Linux; Android 10; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Mobile Safari/537.36"
            }
            chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)

            # Set proxy if provided
            if proxy:
                if 'username' in proxy and 'password' in proxy:
                    # Format: http://username:password@host:port
                    proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
                else:
                    # Format: http://host:port
                    proxy_url = f"http://{proxy['host']}:{proxy['port']}"
                
                self.mobile_driver = seleniumwire_webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=chrome_options
                )
                self.mobile_driver.proxy = proxy_url
                self.mobile_driver.header_overrides = {
                    'Proxy-Authorization': f"Basic {self._encode_proxy_auth(proxy)}" if 'username' in proxy else None
                }
            else:
                self.mobile_driver = seleniumwire_webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=chrome_options
                )

            self.logger.info(f"{Fore.GREEN}[OK] Mobile Browser initialized successfully in headless mode")

        except Exception as e:
            self.logger.error(f"{Fore.RED}[FAIL] Failed to initialize Mobile Browser: {e}")
            raise

    def _setup_csv_logging(self) -> None:
        """Setup CSV logging for search results."""
        self.csv_filename = f"search_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(self.csv_filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                'timestamp', 'generated_query', 'search_url', 
                'response_status', 'execution_time', 'category', 'query_type', 'mode'
            ])
        
        self.logger.info(f"{Fore.CYAN}[LOG] CSV logging initialized: {self.csv_filename}")

    def generate_search_query(self) -> Tuple[str, str, str]:
        """Generate an AI-powered search query using Gemini."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Select random parameters
                category = random.choice(self.search_params["categories"])
                query_type = random.choice(self.search_params["query_types"])
                complexity = random.choice(self.search_params["complexity_levels"])
                
                # Create context-aware prompt
                history_context = ""
                if self.pc_search_history or self.mobile_search_history:
                    recent_searches = self.pc_search_history[-3:] + self.mobile_search_history[-3:]  # Last 3 searches from both modes
                    history_context = f"Recent search topics: {', '.join(recent_searches)}. "
                
                prompt = f"""
                {history_context}Generate a {complexity} {query_type} about {category} that would be suitable for a Bing search.
                
                Requirements:
                - Make it naturally human-like and interesting
                - 3-15 words maximum
                - Avoid repetition of recent topics
                - Be specific enough to get good search results
                - Safe for general audiences
                
                Category: {category}
                Type: {query_type}
                Complexity: {complexity}
                
                Respond with ONLY the search query, nothing else.
                """
                
                response = self.ai_client.generate_content(prompt)
                query = response.text.strip().strip('"').strip("'")
                
                # Validate query
                if self._validate_query(query):
                    self.pc_search_history.append(query)
                    self.mobile_search_history.append(query)
                    if len(self.pc_search_history) > 20:  # Keep only recent history
                        self.pc_search_history = self.pc_search_history[-20:]
                    if len(self.mobile_search_history) > 20:  # Keep only recent history
                        self.mobile_search_history = self.mobile_search_history[-20:]
                    
                    self.logger.info(f"{Fore.YELLOW}[AI] Generated query: {query}")
                    return query, category, query_type
                
            except Exception as e:
                self.logger.warning(f"{Fore.YELLOW}[WARNING] Query generation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt) # Exponential backoff
        
        # Fallback query
        fallback_query = f"what is {random.choice(self.search_params['categories'])}"
        self.logger.warning(f"{Fore.YELLOW}[WARNING] Using fallback query: {fallback_query}")
        return fallback_query, "general", "fallback"

    def _validate_query(self, query: str) -> bool:
        """Validate generated search query."""
        if not query or len(query) < 3:
            return False
        
        if len(query) > 100:  # Too long
            return False
            
        # Check for problematic content
        forbidden_terms = ['explicit', 'illegal', 'hack', 'crack']
        if any(term in query.lower() for term in forbidden_terms):
            return False
            
        return True

    def execute_search(self, query: str, mode: str) -> Tuple[bool, str, float]:
        """Execute search on Bing with human-like behavior and retry on failure."""
        start_time = time.time()
        max_retries = 3  # Number of retries before giving up
        retry_delay = 2  # Delay between retries in seconds
        driver = self.pc_driver if mode == "pc" else self.mobile_driver
        search_history = self.pc_search_history if mode == "pc" else self.mobile_search_history

        for attempt in range(max_retries):
            try:
                # Navigate to Bing
                self.logger.info(f"{Fore.BLUE}[WEB] Navigating to Bing (Attempt {attempt + 1}) in {mode.upper()} mode...")
                driver.get("https://www.bing.com")

                # Wait for the search box to be present
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.ID, "sb_form_q"))
                )

                # Find search box
                search_box = driver.find_element(By.ID, "sb_form_q")

                # Clear any existing text
                search_box.clear()

                # Simulate human-like typing
                self._human_like_typing(search_box, query)

                # Random delay before submitting
                time.sleep(random.uniform(0.5, 2.0))

                # Submit search (randomly choose between Enter key or clicking search button)
                if random.choice([True, False]):
                    search_box.send_keys(Keys.RETURN)
                else:
                    # Wait for the search button to be clickable
                    search_button = WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((By.ID, "search_icon"))
                    )
                    search_button.click()

                # Wait for results
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.ID, "b_results"))
                )

                execution_time = time.time() - start_time
                current_url = driver.current_url

                self.logger.info(f"{Fore.GREEN}[OK] {mode.upper()} search completed successfully in {execution_time:.2f}s (Attempt {attempt + 1})")
                return True, current_url, execution_time

            except TimeoutException:
                self.logger.error(f"{Fore.RED}[TIMEOUT] {mode.upper()} search timeout for query: {query} (Attempt {attempt + 1})")
            except Exception as e:
                self.logger.error(f"{Fore.RED}[FAIL] {mode.upper()} search failed (Attempt {attempt + 1}): {e}")

            # Wait before retrying
            time.sleep(retry_delay)

        # If all retries fail
        execution_time = time.time() - start_time
        self.logger.error(f"{Fore.RED}[FAIL] All retries failed for {mode.upper()} query: {query}")
        return False, "error: all retries failed", execution_time

    def _human_like_typing(self, element, text: str) -> None:
        """Simulate human-like typing with variable speeds and occasional mistakes."""
        for char in text:
            element.send_keys(char)
            # Variable typing speed
            time.sleep(random.uniform(0.05, 0.15))
            
            # Occasional pause (like thinking)
            if random.random() < 0.1:
                time.sleep(random.uniform(0.2, 0.8))

    def _simulate_human_behavior(self, driver) -> None:
        """Simulate human browsing behavior."""
        try:
            actions = ActionChains(driver)
            
            # Random mouse movements
            for _ in range(random.randint(2, 5)):
                x_offset = random.randint(-100, 100)
                y_offset = random.randint(-100, 100)
                actions.move_by_offset(x_offset, y_offset)
            
            actions.perform()
            
            # Random scrolling
            scroll_distance = random.randint(300, 800)
            driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
            
            time.sleep(random.uniform(1, 3))
            
            # Scroll back up sometimes
            if random.random() < 0.3:
                driver.execute_script(f"window.scrollBy(0, -{scroll_distance // 2});")
            
        except Exception as e:
            self.logger.debug(f"Human behavior simulation failed: {e}")

    def _log_search_result(self, query: str, category: str, query_type: str, 
                          success: bool, url: str, execution_time: float, mode: str) -> None:
        """Log search result to CSV file."""
        timestamp = datetime.now().isoformat()
        status = "success" if success else "failed"
        
        with open(self.csv_filename, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                timestamp, query, url, status, f"{execution_time:.2f}",
                category, query_type, mode
            ])

    def _random_delay(self) -> None:
        """Implement random delay between searches."""
        delay = random.randint(self.config['min_delay'], self.config['max_delay'])
        self.logger.info(f"{Fore.CYAN}[WAIT] Waiting {delay} seconds before next search...")
          # Show countdown
        for remaining in range(delay, 0, -1):
            print(f"\r{Fore.CYAN}[WAIT] Next search in: {remaining:2d}s", end="", flush=True)
            time.sleep(1)
        print()  # New line after countdown

    def _recover_from_browser_crash(self, mode: str) -> bool:
        """Attempt to recover from browser crashes."""
        try:
            self.logger.warning(f"{Fore.YELLOW}[RECOVER] Attempting {mode.upper()} browser recovery...")
            
            driver = self.pc_driver if mode == "pc" else self.mobile_driver
            
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            
            time.sleep(5)  # Wait before reinitialization
            
            if mode == "pc":
                self._initialize_pc_browser()
            else:
                self._initialize_mobile_browser()
            
            return True
        except Exception as e:
            self.logger.error(f"{Fore.RED}[FAIL] {mode.upper()} browser recovery failed: {e}")
            return False

    def run(self, pc_cycles: Optional[int] = None, mobile_cycles: Optional[int] = None) -> None:
        """Main execution loop for the search agent."""
        if pc_cycles is None:
            pc_cycles = self.config['max_cycles'] // 1.6875
        if mobile_cycles is None:
            mobile_cycles = self.config['max_cycles'] - pc_cycles
        
        self.logger.info(f"{Fore.MAGENTA}[START] Starting AI Search Agent - PC: {pc_cycles} cycles, Mobile: {mobile_cycles} cycles")
        print(f"\n{Fore.MAGENTA}{'='*60}")
        print(f"{Fore.MAGENTA}[AGENT] Microsoft Rewards Agent - AI Search Automation")
        print(f"{Fore.MAGENTA}{'='*60}")
        print(f"{Fore.CYAN}[INFO] PC Cycles: {pc_cycles}")
        print(f"{Fore.CYAN}[INFO] Mobile Cycles: {mobile_cycles}")
        print(f"{Fore.CYAN}[TIME] Delay Range: {self.config['min_delay']}-{self.config['max_delay']}s")
        print(f"{Fore.CYAN}[LOG] Log File: {self.csv_filename}")
        print(f"{Fore.MAGENTA}{'='*60}\n")
        
        successful_searches = 0
        failed_searches = 0
        
        # Run PC searches first
        if pc_cycles > 0:
            for cycle in range(1, pc_cycles + 1):
                try:
                    print(f"\n{Fore.MAGENTA}[PC CYCLE] Cycle {cycle}/{pc_cycles}")
                    print(f"{Fore.BLUE}{'─'*40}")
                    
                    # Generate AI query
                    query, category, query_type = self.generate_search_query()
                    
                    # Execute search
                    success, url, execution_time = self.execute_search(query, "pc")
                    
                    # Log result
                    self._log_search_result(query, category, query_type, success, url, execution_time, "pc")
                    
                    if success:
                        successful_searches += 1
                        print(f"{Fore.GREEN}[SUCCESS] PC Success: {query}")
                    else:
                        failed_searches += 1
                        print(f"{Fore.RED}[FAIL] PC Failed: {query}")
                    
                    # Progress summary
                    print(f"{Fore.CYAN}[PROGRESS] PC Progress: {successful_searches}/{cycle} successful")
                    
                    # Random delay before next cycle (except for the last cycle)
                    if cycle < pc_cycles:
                        self._random_delay()
                    
                except Exception as e:
                    self.logger.error(f"{Fore.RED}[FAIL] PC Cycle {cycle} failed: {e}")
                    failed_searches += 1
                    
                    # Attempt browser recovery
                    if "driver" in str(e).lower() or "session" in str(e).lower():
                        if not self._recover_from_browser_crash("pc"):
                            self.logger.error(f"{Fore.RED}[FAIL] Cannot continue - browser recovery failed")
                            break
        
        # Run Mobile searches next
        if mobile_cycles > 0:
            for cycle in range(1, mobile_cycles + 1):
                try:
                    print(f"\n{Fore.MAGENTA}[MOBILE CYCLE] Cycle {cycle}/{mobile_cycles}")
                    print(f"{Fore.BLUE}{'─'*40}")
                    
                    # Generate AI query
                    query, category, query_type = self.generate_search_query()
                    
                    # Execute search
                    success, url, execution_time = self.execute_search(query, "mobile")
                    
                    # Log result
                    self._log_search_result(query, category, query_type, success, url, execution_time, "mobile")
                    
                    if success:
                        successful_searches += 1
                        print(f"{Fore.GREEN}[SUCCESS] Mobile Success: {query}")
                    else:
                        failed_searches += 1
                        print(f"{Fore.RED}[FAIL] Mobile Failed: {query}")
                    
                    # Progress summary
                    print(f"{Fore.CYAN}[PROGRESS] Mobile Progress: {successful_searches}/{cycle} successful")
                    
                    # Random delay before next cycle (except for the last cycle)
                    if cycle < mobile_cycles:
                        self._random_delay()
                    
                except Exception as e:
                    self.logger.error(f"{Fore.RED}[FAIL] Mobile Cycle {cycle} failed: {e}")
                    failed_searches += 1
                    
                    # Attempt browser recovery
                    if "driver" in str(e).lower() or "session" in str(e).lower():
                        if not self._recover_from_browser_crash("mobile"):
                            self.logger.error(f"{Fore.RED}[FAIL] Cannot continue - browser recovery failed")
                            break
        
        # Final summary
        self._print_final_summary(successful_searches, failed_searches, pc_cycles + mobile_cycles)

    def _print_final_summary(self, successful: int, failed: int, total_planned: int) -> None:
        """Print execution summary."""
        total_executed = successful + failed
        success_rate = (successful / total_executed * 100) if total_executed > 0 else 0
        session_duration = datetime.now() - self.session_start_time
        
        print(f"\n{Fore.MAGENTA}{'='*60}")
        print(f"{Fore.MAGENTA}[SUMMARY] EXECUTION SUMMARY")
        print(f"{Fore.MAGENTA}{'='*60}")
        print(f"{Fore.GREEN}[SUCCESS] Successful searches: {successful}")
        print(f"{Fore.RED}[FAIL] Failed searches: {failed}")
        print(f"{Fore.CYAN}[STATS] Success rate: {success_rate:.1f}%")
        print(f"{Fore.CYAN}[TIME] Session duration: {session_duration}")
        print(f"{Fore.CYAN}[LOG] Results logged to: {self.csv_filename}")
        print(f"{Fore.MAGENTA}{'='*60}\n")

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.pc_driver:
                self.pc_driver.quit()
                self.logger.info(f"{Fore.GREEN}[OK] PC Browser cleanup completed")
            if self.mobile_driver:
                self.mobile_driver.quit()
                self.logger.info(f"{Fore.GREEN}[OK] Mobile Browser cleanup completed")
        except Exception as e:
            self.logger.warning(f"{Fore.YELLOW}[WARNING] Cleanup warning: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()

    def load_credentials(self, filename='credentials.json'):
        """Load Microsoft account credentials from a JSON file."""
        try:
            with open(filename, 'r') as f:
                self.credentials = json.load(f)
            self.logger.info(f"{Fore.GREEN}[OK] Loaded {len(self.credentials['accounts'])} accounts")
        except Exception as e:
            self.logger.error(f"{Fore.RED}[FAIL] Failed to load credentials: {e}")
            self.credentials = None

    def login_to_account(self, email, password, driver):
        """Log in to a Microsoft account."""
        try:
            driver.get("https://login.live.com")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "i0116")))

            # Enter email
            email_field = driver.find_element(By.ID, "i0116")
            email_field.clear()
            email_field.send_keys(email)
            driver.find_element(By.ID, "idSIButton9").click()

            # Enter password
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "i0118")))
            password_field = driver.find_element(By.ID, "i0118")
            password_field.clear()
            password_field.send_keys(password)
            driver.find_element(By.ID, "idSIButton9").click()

            # Handle 'Stay signed in' prompt
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "idSIButton9")))
            driver.find_element(By.ID, "idSIButton9").click()

            self.logger.info(f"{Fore.GREEN}[OK] Logged in to {email}")
            return True
        except Exception as e:
            self.logger.error(f"{Fore.RED}[FAIL] Failed to log in to {email}: {e}")
            return False

    def run_with_multiple_accounts(self):
        """Run the search agent for multiple accounts."""
        if not hasattr(self, 'credentials') or not self.credentials:
            self.logger.error(f"{Fore.RED}[FAIL] No credentials loaded")
            return

        for account in self.credentials['accounts']:
            email = account['email']
            password = account['password']

            # Select a proxy
            proxy = self._get_next_proxy()

            # Initialize PC driver
            self.pc_driver = None
            self._initialize_pc_browser(proxy)

            # Log in to the account
            if self.login_to_account(email, password, self.pc_driver):
                # Perform searches for this account
                self.pc_search_history = []
                self.mobile_search_history = []
                self.run(pc_cycles=self.config['max_cycles'], mobile_cycles=0)

            # Clean up PC driver
            if self.pc_driver:
                self.pc_driver.quit()

            # Initialize Mobile driver
            self.mobile_driver = None
            self._initialize_mobile_browser(proxy)

            # Log in to the account again for mobile searches
            if self.login_to_account(email, password, self.mobile_driver):
                # Perform mobile searches for this account
                self.run(pc_cycles=0, mobile_cycles=self.config['max_cycles'])

            # Clean up Mobile driver
            if self.mobile_driver:
                self.mobile_driver.quit()

            self.logger.info(f"{Fore.GREEN}[OK] Completed processing for {email}")

    def _get_next_proxy(self):
        """Get the next available proxy from the list."""
        if not self.proxies:
            self.logger.warning(f"{Fore.YELLOW}[WARNING] No proxies available")
            return None
        
        # Simple round-robin approach
        if not hasattr(self, 'current_proxy_index'):
            self.current_proxy_index = 0
        else:
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        
        return self.proxies[self.current_proxy_index]


def main():
    """Main entry point."""
    try:
        with AISearchAgent() as agent:
            agent.load_credentials()
            agent.run_with_multiple_accounts()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[WARNING] Program interrupted by user")
    except Exception as e:
        print(f"\n{Fore.RED}[FATAL] Fatal error: {e}")
        if 'agent' in locals() and agent.config.get('debug_mode'):
            traceback.print_exc()
    finally:
        print(f"\n{Fore.CYAN}[EXIT] AI Search Agent terminated")


if __name__ == "__main__":
    main()
