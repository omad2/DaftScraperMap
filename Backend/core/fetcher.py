import requests
import json
from typing import Optional, Dict, Any
from loguru import logger
from config import config
from models import ScrapedProperty
from bs4 import BeautifulSoup
from exceptions import (
    ScrapingException, NetworkException, RateLimitException,
    ConfigurationException
)

class Fetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        })

    def fetch_page_html(self, url: str, page_number: int = 0) -> Optional[str]:
        for attempt in range(1, config.MAX_FETCH_RETRIES + 2):
            logger.info(f"Fetching HTML for page {page_number} from {url} (Attempt {attempt})")
            
            try:
                if page_number == 1 and attempt == 1:
                    try:
                        main_response = self.session.get('https://www.daft.ie', timeout=config.REQUEST_TIMEOUT)
                        logger.info(f"Main page access: {main_response.status_code}")
                        from utils import delay
                        delay(1000)
                    except:
                        pass
                
                response = self.session.get(
                    url, 
                    timeout=config.REQUEST_TIMEOUT
                )
                
                if response.status_code == 404:
                    logger.warning(f"Page {page_number} not found (404): {url}. Skipping.")
                    raise ScrapingException(
                        f"Page not found: {url}",
                        url=url,
                        status_code=404
                    )
                
                if response.status_code == 403:
                    logger.warning(f"Access forbidden (403) for page {page_number}: {url}. This might be due to anti-bot protection.")
                    if attempt <= config.MAX_FETCH_RETRIES:
                        from utils import delay
                        delay(config.RETRY_DELAY_MS * 2)
                        continue
                    else:
                        raise RateLimitException(
                            f"Access forbidden after {config.MAX_FETCH_RETRIES} retries: {url}",
                            retry_after=config.RETRY_DELAY_MS * 2,
                            details={"url": url, "status_code": 403}
                        )
                
                response.raise_for_status()
                logger.info(f"HTML fetched successfully for page {page_number}. Status: {response.status_code}, Length: {len(response.text)}")
                return response.text
                
            except requests.exceptions.Timeout as e:
                logger.error(f"Timeout fetching page {page_number} (Attempt {attempt}): {str(e)}")
                if attempt > config.MAX_FETCH_RETRIES:
                    raise NetworkException(
                        f"Timeout fetching page {page_number} after {config.MAX_FETCH_RETRIES} retries",
                        url=url,
                        timeout=True,
                        details={"attempt": attempt, "timeout": config.REQUEST_TIMEOUT}
                    )
                from utils import delay
                delay(config.RETRY_DELAY_MS)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching page {page_number} (Attempt {attempt}): {str(e)}")
                
                if attempt > config.MAX_FETCH_RETRIES:
                    logger.error(f"Max retries reached for page {page_number}. Giving up.")
                    raise NetworkException(
                        f"Failed to fetch page {page_number} after {config.MAX_FETCH_RETRIES} retries: {str(e)}",
                        url=url,
                        details={"attempt": attempt, "error": str(e)}
                    )
                
                if attempt <= config.MAX_FETCH_RETRIES:
                    from utils import delay
                    delay(config.RETRY_DELAY_MS)
        
        raise NetworkException(
            f"Failed to fetch page {page_number} after multiple retries",
            url=url,
            details={"max_retries": config.MAX_FETCH_RETRIES}
        )

    def fetch_json_api(self, url: str, page_number: int = 0) -> Optional[Dict[Any, Any]]:
        for attempt in range(1, config.MAX_FETCH_RETRIES + 2):
            logger.info(f"Fetching JSON for page {page_number} from {url} (Attempt {attempt})")
            
            try:
                json_headers = self.session.headers.copy()
                json_headers.update({
                    'Accept': 'application/json, text/plain, */*',
                    'Referer': 'https://www.daft.ie/',
                    'X-Requested-With': 'XMLHttpRequest'
                })
                
                response = self.session.get(
                    url, 
                    headers=json_headers,
                    timeout=config.REQUEST_TIMEOUT
                )
                
                if response.status_code == 404:
                    logger.warning(f"API endpoint not found (404): {url}. Skipping.")
                    raise ScrapingException(
                        f"API endpoint not found: {url}",
                        url=url,
                        status_code=404
                    )
                
                if response.status_code == 403:
                    logger.warning(f"Access forbidden (403) for API endpoint: {url}. This might be due to anti-bot protection.")
                    if attempt <= config.MAX_FETCH_RETRIES:
                        from utils import delay
                        delay(config.RETRY_DELAY_MS * 2)
                        continue
                    else:
                        raise RateLimitException(
                            f"Access forbidden for API endpoint after {config.MAX_FETCH_RETRIES} retries: {url}",
                            retry_after=config.RETRY_DELAY_MS * 2,
                            details={"url": url, "status_code": 403}
                        )
                
                response.raise_for_status()
                
                try:
                    json_data = response.json()
                    logger.info(f"JSON fetched successfully for page {page_number}. Status: {response.status_code}")
                    return json_data
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {str(e)}")
                    raise ScrapingException(
                        f"Invalid JSON response from API: {url}",
                        url=url,
                        details={"json_error": str(e)}
                    )
                
            except requests.exceptions.Timeout as e:
                logger.error(f"Timeout fetching JSON for page {page_number} (Attempt {attempt}): {str(e)}")
                if attempt > config.MAX_FETCH_RETRIES:
                    raise NetworkException(
                        f"Timeout fetching JSON for page {page_number} after {config.MAX_FETCH_RETRIES} retries",
                        url=url,
                        timeout=True,
                        details={"attempt": attempt, "timeout": config.REQUEST_TIMEOUT}
                    )
                from utils import delay
                delay(config.RETRY_DELAY_MS)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching JSON for page {page_number} (Attempt {attempt}): {str(e)}")
                
                if attempt > config.MAX_FETCH_RETRIES:
                    logger.error(f"Max retries reached for page {page_number}. Giving up.")
                    raise NetworkException(
                        f"Failed to fetch JSON for page {page_number} after {config.MAX_FETCH_RETRIES} retries: {str(e)}",
                        url=url,
                        details={"attempt": attempt, "error": str(e)}
                    )
                
                if attempt <= config.MAX_FETCH_RETRIES:
                    from utils import delay
                    delay(config.RETRY_DELAY_MS)
        
        raise NetworkException(
            f"Failed to fetch JSON for page {page_number} after multiple retries",
            url=url,
            details={"max_retries": config.MAX_FETCH_RETRIES}
        )


    def get_build_id(self) -> str:
        try:
            response = self.session.get(config.DAFT_BASE_URL, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
            
            if not script_tag or not script_tag.string:
                raise ScrapingException(
                    "Could not find __NEXT_DATA__ script tag",
                    url=config.DAFT_BASE_URL,
                    details={"html_length": len(response.text)}
                )
            
            data = json.loads(script_tag.string)
            build_id = data.get('buildId')
            
            if not build_id:
                raise ScrapingException(
                    "buildId not present in __NEXT_DATA__",
                    url=config.DAFT_BASE_URL,
                    details={"data_keys": list(data.keys())}
                )
            
            logger.info(f"Extracted build ID: {build_id}")
            return build_id
            
        except (ScrapingException, NetworkException):
            raise
        except Exception as e:
            logger.error(f"Failed to extract build ID: {str(e)}")
            logger.warning("Using fallback build ID")
            return "eYQ3CuRxzsMJz17gSBSMk"

    def fetch_search_results_json(self, search_path: str, page: int = 1) -> Optional[Dict[Any, Any]]:
        try:
            url = f"{config.DAFT_BASE_URL}{search_path}?page={page}"
            logger.info(f"Fetching search results from: {url}")
            
            response = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
            
            if not script_tag or not script_tag.string:
                logger.warning(f"No __NEXT_DATA__ found on page {page}")
                return None
            
            data = json.loads(script_tag.string)
            logger.info(f"Successfully extracted __NEXT_DATA__ from page {page}")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching search results for page {page}: {str(e)}")
            return None

    def build_property_api_url(self, property_id: str, address_slug: str) -> str:
        """Build API URL for individual property details using dynamic build ID"""
        try:
            build_id = self.get_build_id()
        except:
            # Fallback to hardcoded build ID
            build_id = "eYQ3CuRxzsMJz17gSBSMk"
        
        api_url = f"{config.DAFT_BASE_URL}/_next/data/{build_id}/property.json?id={property_id}&address={address_slug}"
        logger.info(f"Constructed property API URL: {api_url}")
        return api_url

    def close(self):
        """Close the session"""
        self.session.close()
