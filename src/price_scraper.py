"""Price scraper for extracting prices from product pages."""

import json
import re
from typing import TYPE_CHECKING, Any, Dict, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Playwright


class PriceScraper:
    """Scraper for extracting prices from various e-commerce websites."""

    def __init__(self, timeout: int = 10, use_browser: bool = True):
        """Initialize the price scraper.

        Args:
            timeout: Request timeout in seconds
            use_browser: Whether to use Playwright for JavaScript-heavy sites
        """
        self.timeout = timeout
        self.use_browser = use_browser
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self._playwright: Optional["Playwright"] = None
        self._browser: Optional["Browser"] = None

    def __enter__(self) -> "PriceScraper":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - cleanup browser."""
        self.close()

    def close(self) -> None:
        """Close browser resources."""
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def _get_page_with_browser(self, url: str) -> Optional[str]:
        """Fetch page content using Playwright browser."""
        if not self.use_browser:
            return None

        try:
            from playwright.sync_api import sync_playwright

            if not self._playwright:
                self._playwright = sync_playwright().start()
                self._browser = self._playwright.chromium.launch(headless=True)

            if self._browser is None:
                raise RuntimeError("Browser failed to launch")
            page = self._browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=self.timeout * 1000)

            # Wait a bit for any dynamic content to load
            page.wait_for_timeout(2000)

            content = page.content()
            page.close()

            return content
        except ImportError:
            print("Warning: playwright not installed, falling back to requests")
            return None
        except Exception as e:
            print(f"Error using browser: {e}")
            return None

    def fetch_price(self, url: str) -> Optional[float]:
        """Fetch the price from a given URL.

        Args:
            url: The product page URL

        Returns:
            The price as a float, or None if extraction failed
        """
        try:
            domain = urlparse(url).netloc

            # For Willys, use browser to render JavaScript
            if "willys.se" in domain and self.use_browser:
                html_content = self._get_page_with_browser(url)
                if html_content:
                    soup = BeautifulSoup(html_content, "html.parser")
                    return self._scrape_willys(soup)

            # For other sites, use regular requests
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Try JSON-LD first (works for many sites)
            price = self._extract_from_jsonld(soup)
            if price:
                return price

            # Try Next.js/React data
            price = self._extract_from_nextjs_data(response.text)
            if price:
                return price

            # Route to appropriate scraper based on domain
            if "jula.se" in domain:
                return self._scrape_jula(soup)
            elif "willys.se" in domain:
                return self._scrape_willys(soup)
            else:
                # Generic price extraction for unknown sites
                return self._scrape_generic(soup)

        except Exception as e:
            print(f"Error fetching price from {url}: {e}")
            return None

    def _extract_from_nextjs_data(self, html: str) -> Optional[float]:
        """Extract price from Next.js __NEXT_DATA__ or similar embedded JSON."""
        try:
            # Look for __NEXT_DATA__ in script tag with id
            match = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
                html,
                re.DOTALL,
            )
            if match:
                try:
                    data = json.loads(match.group(1))
                    price = self._find_price_in_dict(data)
                    if price:
                        return price
                except json.JSONDecodeError:
                    pass

            # Fallback to other patterns
            patterns = [
                r"__NEXT_DATA__\s*=\s*({.+?})\s*</script>",
                r"__INITIAL_STATE__\s*=\s*({.+?})\s*</script>",
                r"window\.__PRELOADED_STATE__\s*=\s*({.+?})\s*</script>",
            ]

            for pattern in patterns:
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        price = self._find_price_in_dict(data)
                        if price:
                            return price
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
        return None

    def _find_price_in_dict(
        self, data: Dict[str, Any], depth: int = 0
    ) -> Optional[float]:
        """Recursively search for price in nested dictionaries."""
        if depth > 10:  # Prevent infinite recursion
            return None

        # Look for common price field names
        price_keys = [
            "price",
            "currentPrice",
            "sellingPrice",
            "salePrice",
            "priceValue",
            "unitPrice",
            "amount",
            "value",
            "priceAmount",
            "retailPrice",
            "displayPrice",
            "listPrice",
            "regularPrice",
        ]

        for key in price_keys:
            if key in data:
                try:
                    value = data[key]
                    if isinstance(value, (int, float)):
                        return float(value)
                    elif isinstance(value, str):
                        extracted = self._extract_number(value)
                        if extracted:
                            return extracted
                    elif isinstance(value, dict):
                        # Sometimes price is nested like {"price": {"amount": 39.80}}
                        for subkey in ["amount", "value", "price"]:
                            if subkey in value:
                                try:
                                    return float(value[subkey])
                                except (ValueError, TypeError, KeyError):
                                    pass
                except (ValueError, TypeError, KeyError):
                    pass

        # Recursively search nested structures
        for key, value in data.items():
            if isinstance(value, dict):
                price = self._find_price_in_dict(value, depth + 1)
                if price:
                    return price
            elif isinstance(value, list) and depth < 5:  # Limit list searching depth
                for item in value[:20]:  # Limit items checked in lists
                    if isinstance(item, dict):
                        price = self._find_price_in_dict(item, depth + 1)
                        if price:
                            return price

        return None

    def _extract_from_jsonld(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract price from JSON-LD structured data."""
        try:
            for script in soup.find_all("script", type="application/ld+json"):
                if not script.string:
                    continue
                try:
                    data = json.loads(script.string)
                    # Handle both single objects and arrays
                    if isinstance(data, list):
                        for item in data:
                            price = self._extract_price_from_jsonld_object(item)
                            if price:
                                return price
                    else:
                        price = self._extract_price_from_jsonld_object(data)
                        if price:
                            return price
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass
        return None

    def _extract_price_from_jsonld_object(
        self, data: Dict[str, Any]
    ) -> Optional[float]:
        """Extract price from a JSON-LD object."""
        # Direct price field
        if "price" in data:
            try:
                return float(data["price"])
            except (ValueError, TypeError):
                pass

        # Offers structure
        if "offers" in data:
            offers = data["offers"]
            if isinstance(offers, dict):
                if "price" in offers:
                    try:
                        return float(offers["price"])
                    except (ValueError, TypeError):
                        pass
            elif isinstance(offers, list) and offers:
                first_offer = offers[0]
                if "price" in first_offer:
                    try:
                        return float(first_offer["price"])
                    except (ValueError, TypeError):
                        pass

        return None

    def _scrape_jula(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract price from Jula.se."""
        try:
            # Look for common price selectors on Jula
            price_selectors = [
                {"class": "price"},
                {"class": "product-price"},
                {"itemprop": "price"},
                {"class": re.compile("price", re.I)},
            ]

            for selector in price_selectors:
                element = soup.find(attrs=selector)  # type: ignore[arg-type]
                if element:
                    price_text = element.get_text(strip=True)
                    price = self._extract_number(price_text)
                    if price:
                        return price

            # Try meta tags
            meta_price = soup.find("meta", property="product:price:amount")
            if meta_price and hasattr(meta_price, "get") and meta_price.get("content"):
                content = meta_price.get("content")
                if isinstance(content, str):
                    return float(content)

        except Exception as e:
            print(f"Error scraping Jula: {e}")

        return None

    def _scrape_willys(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract price from Willys.se."""
        try:
            # Willys splits price into separate spans: <span>22</span> ... <span>90</span><span>/st</span>
            # Strategy: Find the "/st" marker and extract numbers from the parent container

            st_spans = soup.find_all(string=re.compile(r"/st"))

            for st_span in st_spans:
                # Navigate up the tree to find the container with price parts
                parent = st_span.parent
                for _ in range(5):  # Check up to 5 levels up
                    if parent is None:
                        break

                    # Get all spans from this container
                    all_spans = parent.find_all("span")
                    texts = [s.get_text(strip=True) for s in all_spans]

                    # Find numeric texts (price parts)
                    numbers = []
                    for text in texts:
                        # Skip the /st marker itself
                        if "/st" in text or "/kg" in text or "/l" in text:
                            continue
                        # Check if it's a 1-4 digit number
                        if text.isdigit() and 1 <= len(text) <= 4:
                            numbers.append(text)

                    # If we found at least 2 numbers, try to combine them
                    if len(numbers) >= 2:
                        try:
                            # Try different combinations to find a reasonable price
                            # Common pattern: ignore leading zeros or small numbers
                            for i in range(len(numbers) - 1):
                                whole_part = numbers[i]
                                decimal_part = numbers[i + 1]
                                
                                # Skip if whole part is "0" or "00" (likely not the actual price)
                                if whole_part in ["0", "00"]:
                                    continue
                                    
                                price = float(f"{whole_part}.{decimal_part}")
                                
                                # Sanity check: reasonable price range (at least 1 kr)
                                if 1 <= price < 10000:
                                    return price
                        except (ValueError, IndexError):
                            pass

                    parent = parent.parent

            # Fallback: Original methods
            price_selectors = [
                {"class": re.compile("price", re.I)},
                {"data-testid": "product-price"},
                {"class": "product-price"},
                {"itemprop": "price"},
            ]

            for selector in price_selectors:
                element = soup.find(attrs=selector)  # type: ignore[arg-type]
                if element:
                    price_text = element.get_text(strip=True)
                    extracted_price = self._extract_number(price_text)
                    if extracted_price:
                        return extracted_price

            # Try meta tags
            meta_price = soup.find("meta", property="product:price:amount")
            if meta_price and hasattr(meta_price, "get") and meta_price.get("content"):
                content = meta_price.get("content")
                if isinstance(content, str):
                    return float(content)

        except Exception as e:
            print(f"Error scraping Willys: {e}")

        return None

    def _scrape_generic(self, soup: BeautifulSoup) -> Optional[float]:
        """Generic price extraction for unknown websites."""
        try:
            # Try meta tags first
            meta_price = soup.find("meta", property="product:price:amount")
            if meta_price and hasattr(meta_price, "get") and meta_price.get("content"):
                content = meta_price.get("content")
                if isinstance(content, str):
                    return float(content)

            # Look for common price patterns
            price_selectors = [
                {"class": re.compile("price", re.I)},
                {"itemprop": "price"},
                {"id": re.compile("price", re.I)},
            ]

            for selector in price_selectors:
                element = soup.find(attrs=selector)  # type: ignore[arg-type]
                if element:
                    price_text = element.get_text(strip=True)
                    price = self._extract_number(price_text)
                    if price:
                        return price

        except Exception as e:
            print(f"Error in generic scraper: {e}")

        return None

    def _extract_number(self, text: str) -> Optional[float]:
        """Extract a numeric price from text.

        Handles various formats like:
        - 199 kr
        - 199,00 kr
        - 199.00
        - kr 199
        - $199.99

        Args:
            text: The text containing the price

        Returns:
            The extracted price as a float, or None if not found
        """
        # Remove currency symbols and common text
        text = re.sub(r"kr|SEK|\$|€|£", "", text, flags=re.I)

        # Replace comma with dot for decimal separator
        text = text.replace(",", ".")

        # Extract all numbers (including decimals)
        matches = re.findall(r"\d+\.?\d*", text)

        if matches:
            # Take the first number found
            try:
                return float(matches[0])
            except ValueError:
                pass

        return None
