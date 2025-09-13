import re
import json
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from loguru import logger
from models import ScrapedProperty, ParsedPriceResult, ParsedBedsResult
from core.utils import parse_price, parse_beds, parse_bathrooms, extract_lat_lng, format_ber
from config import config
from datetime import datetime

class Parser:
    def __init__(self):
        pass

    def parse_search_results(self, html: str) -> List[ScrapedProperty]:
        soup = BeautifulSoup(html, 'html.parser')
        properties = []
        
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
        if script_tag and script_tag.string:
            try:
                data = json.loads(script_tag.string)
                raw_listings = data.get("props", {}).get("pageProps", {}).get("listings", [])
                
                if raw_listings:
                    logger.info(f"Found {len(raw_listings)} listings in __NEXT_DATA__")
                    for item in raw_listings:
                        try:
                            listing_data = item.get("listing", {})
                            if listing_data:
                                wrapped_data = {"pageProps": {"listing": listing_data}}
                                property_data = self.parse_property_details_json(wrapped_data, 'sale')
                                if property_data:
                                    properties.append(property_data)
                        except Exception as e:
                            logger.error(f"Error parsing listing from __NEXT_DATA__: {str(e)}")
                            continue
                    
                    logger.info(f"Parsed {len(properties)} properties from __NEXT_DATA__")
                    return properties
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse __NEXT_DATA__ JSON: {str(e)}")
        
        logger.info("Falling back to HTML parsing")
        property_elements = soup.select('[data-testid="card-container"]')
        
        for element in property_elements:
            try:
                property_data = self._parse_property_element(element)
                if property_data:
                    properties.append(property_data)
            except Exception as e:
                logger.error(f"Error parsing property element: {str(e)}")
                continue
        
        logger.info(f"Parsed {len(properties)} properties from search results")
        return properties

    def _parse_property_element(self, element) -> Optional[ScrapedProperty]:
        try:
            address_elem = element.select_one('div[data-tracking="srp_address"] p')
            address = address_elem.get_text(strip=True) if address_elem else ""

            main_link = element.select_one('a')
            if not main_link:
                return None
                
            relative_url = main_link.get('href')
            if not relative_url:
                return None
                
            url = f"{config.DAFT_BASE_URL}{relative_url}"
            url_parts = relative_url.strip('/').split('/')
            property_id = url_parts[-1] if url_parts else ""

            tagline_elem = element.select_one('div[data-tracking="srp_tagline"] p')
            tagline = tagline_elem.get_text(strip=True) if tagline_elem else ""

            price_elem = element.select_one('div[data-tracking="srp_price"] p')
            price_string = price_elem.get_text(strip=True) if price_elem else ""
            parsed_price_result = parse_price(price_string)
            
            meta_elem = element.select_one('div[data-tracking="srp_meta"]')
            beds_string = ""
            baths_string = ""
            property_type_string = ""
            
            if meta_elem:
                spans = meta_elem.select('span')
                for span in spans:
                    text = span.get_text(strip=True)
                    if 'Bed' in text:
                        beds_string = text
                    elif 'Bath' in text:
                        baths_string = text
                    elif any(ptype in text.lower() for ptype in ['apartment', 'house', 'duplex', 'terrace', 'detached', 'semi-detached']):
                        property_type_string = text
            
            parsed_beds = parse_beds(beds_string)

            ber = self._extract_ber(element)

            lat_lng = self._extract_coordinates(element)

            image_url = self._extract_image_url(element)

            return ScrapedProperty(
                address=address,
                url=url,
                id=property_id,
                tagline=tagline,
                price_string=price_string,
                parsed_price=parsed_price_result.value,
                price_type=parsed_price_result.type,
                beds_string=beds_string,
                parsed_beds=parsed_beds,
                baths_string=baths_string,
                property_type_string=property_type_string,
                ber=ber,
                latitude=lat_lng['lat'] if lat_lng else None,
                longitude=lat_lng['lng'] if lat_lng else None,
                image_url=image_url
            )
            
        except Exception as e:
            logger.error(f"Error parsing property element: {str(e)}")
            return None

    def _extract_price(self, element) -> str:
        price_selectors = [
            'p[data-testid="price"]',
            '[class*="TitleBlock__StyledSpan"][class*="price"]',
            'p.csEcJw',
            'div[data-testid="card-price"] p',
        ]
        
        for selector in price_selectors:
            price_elem = element.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                if price_text:
                    return price_text
        
        potential_price_elem = element.select_one('p[class^="sc-4c172e97-0"]')
        if potential_price_elem:
            potential_price_text = potential_price_elem.get_text(strip=True)
            if ('€' in potential_price_text or 
                re.search(r'per (month|week)', potential_price_text, re.IGNORECASE) or
                re.search(r'POA|price on application', potential_price_text, re.IGNORECASE)):
                return potential_price_text
        
        return ""

    def _extract_ber(self, element) -> Optional[str]:
        ber_selectors = [
            'div[data-testid="callout-container"] [aria-label^="BER"]',
            'div[data-tracking="srp_ber"]',
            'p[data-testid="ber"]'
        ]
        
        for selector in ber_selectors:
            ber_elem = element.select_one(selector)
            if ber_elem:
                ber_text = ber_elem.get('aria-label') or ber_elem.get_text(strip=True)
                if ber_text:
                    return format_ber(ber_text)
        
        return None

    def _extract_coordinates(self, element) -> Optional[Dict[str, float]]:
        lat_lng_elem = element.select_one('div.sc-eb305aa9-35.jfAOAq')
        if lat_lng_elem:
            return extract_lat_lng(str(lat_lng_elem))
        return None

    def _extract_image_url(self, element) -> Optional[str]:
        img_elem = element.select_one('img')
        if img_elem:
            return img_elem.get('src') or img_elem.get('data-src')
        return None

    def parse_property_details(self, html: str, property_data: ScrapedProperty) -> ScrapedProperty:
        soup = BeautifulSoup(html, 'html.parser')
        
        lat_lng_elem = soup.select_one('div.sc-eb305aa9-35.jfAOAq')
        if lat_lng_elem:
            lat_lng = extract_lat_lng(str(lat_lng_elem))
            if lat_lng:
                property_data.latitude = lat_lng['lat']
                property_data.longitude = lat_lng['lng']

        if not property_data.ber:
            ber_selectors = [
                'div[data-testid="callout-container"] [aria-label^="BER"]',
                'p[data-testid="ber"]',
                'div[data-testid="ber-container"] p'
            ]
            
            for selector in ber_selectors:
                ber_elem = soup.select_one(selector)
                if ber_elem:
                    ber_text = ber_elem.get('aria-label') or ber_elem.get_text(strip=True)
                    if ber_text:
                        property_data.ber = format_ber(ber_text)
                        break

        date_elem = soup.select_one('[data-testid="date-listed"]')
        if date_elem:
            date_text = date_elem.get_text(strip=True)
            pass

        return property_data

    def get_total_pages(self, html: str) -> int:
        soup = BeautifulSoup(html, 'html.parser')
        
        total_results_elem = soup.select_one('span.sc-4c172e97-0.ioLdWh')
        if total_results_elem:
            total_results_text = total_results_elem.get_text(strip=True)
            logger.info(f"Found total results string: '{total_results_text}'")
            
            match = re.search(r'of\s*([\d,]+)\s*total results', total_results_text, re.IGNORECASE)
            if match:
                try:
                    total_results = int(match.group(1).replace(',', ''))
                    calculated_pages = (total_results + 19) // 20
                    total_pages = min(calculated_pages, config.MAX_PAGES_TO_FETCH)
                    
                    if calculated_pages > config.MAX_PAGES_TO_FETCH:
                        logger.warning(f"Calculated total pages ({calculated_pages}) exceeds max pages ({config.MAX_PAGES_TO_FETCH}). Capping at {total_pages}.")
                    
                    logger.info(f"Extracted total results: {total_results}, calculated pages: {calculated_pages}, effective total pages: {total_pages}")
                    return total_pages
                except ValueError:
                    pass
        
        return 1



    def parse_property_details_json(self, json_data: Dict[Any, Any], listing_type: str = 'sale') -> Optional[ScrapedProperty]:
        try:
            page_props = json_data.get('pageProps', {})
            listing = page_props.get('listing', {})
            
            if not listing:
                logger.warning("No listing found in property details JSON")
                return None
            
            property_id = str(listing.get('id', ''))
            title = listing.get('title', '')
            price = listing.get('price', '')
            num_bedrooms = listing.get('numBedrooms', '')
            num_bathrooms = listing.get('numBathrooms', '')
            property_type = listing.get('propertyType', '')
            daft_shortcode = listing.get('daftShortcode', property_id)
            
            seo_friendly_path = listing.get('seoFriendlyPath', '')
            if seo_friendly_path:
                url = f"{config.DAFT_BASE_URL}{seo_friendly_path}"
            else:
                if listing_type == 'rent':
                    url = f"{config.DAFT_BASE_URL}/property-for-rent/property-{daft_shortcode}"
                else:
                    url = f"{config.DAFT_BASE_URL}/property-for-sale/property-{daft_shortcode}"
            
            parsed_price_result = parse_price(price)
            
            parsed_beds = parse_beds(num_bedrooms)
            
            latitude = None
            longitude = None
            if 'point' in listing:
                point = listing['point']
                coordinates = point.get('coordinates', [])
                if len(coordinates) >= 2:
                    longitude = float(coordinates[0])
                    latitude = float(coordinates[1])
            elif 'location' in listing:
                location = listing['location']
                latitude = location.get('lat')
                longitude = location.get('lon')
            
            image_url = None
            if 'media' in listing and 'images' in listing['media']:
                images = listing['media']['images']
                if images and len(images) > 0:
                    first_image = images[0]
                    image_url = (first_image.get('size720x480') or 
                               first_image.get('size600x600') or
                               first_image.get('size400x300') or
                               first_image.get('size360x240') or 
                               first_image.get('size300x200'))
            
            date_listed = None
            publish_date = listing.get('publishDate')
            if publish_date:
                try:
                    date_listed = datetime.fromisoformat(publish_date.replace('Z', '+00:00'))
                except:
                    pass
            
            ber = None
            if 'ber' in listing:
                ber_data = listing['ber']
                if isinstance(ber_data, dict):
                    ber = ber_data.get('rating', None)
                elif isinstance(ber_data, str):
                    ber = ber_data
            
            return ScrapedProperty(
                address=title,
                url=url,
                id=property_id,
                tagline=title,
                price_string=price,
                parsed_price=parsed_price_result.value,
                price_type=parsed_price_result.type,
                beds_string=num_bedrooms,
                parsed_beds=parsed_beds,
                baths_string=num_bathrooms,
                property_type_string=property_type,
                ber=ber,
                latitude=float(latitude) if latitude else None,
                longitude=float(longitude) if longitude else None,
                image_url=image_url,
                date_listed=date_listed
            )
            
        except Exception as e:
            logger.error(f"Error parsing property details JSON: {str(e)}")
            return None

    def get_total_pages_from_json(self, json_data: Dict[Any, Any]) -> int:
        try:
            page_props = json_data.get('pageProps', {})
            pagination = page_props.get('pagination', {})
            
            if 'totalPages' in pagination:
                total_pages = pagination['totalPages']
                total_pages = min(total_pages, config.MAX_PAGES_TO_FETCH)
                logger.info(f"Found total pages from JSON: {total_pages}")
                return total_pages
            
            total_results = pagination.get('totalResults', 0)
            if total_results > 0:
                results_per_page = pagination.get('resultsPerPage', 20)
                calculated_pages = (total_results + results_per_page - 1) // results_per_page
                total_pages = min(calculated_pages, config.MAX_PAGES_TO_FETCH)
                logger.info(f"Calculated total pages from JSON: {total_pages} (from {total_results} results)")
                return total_pages
            
            return 1
            
        except Exception as e:
            logger.error(f"Error getting total pages from JSON: {str(e)}")
            return 1

    def parse_next_data_search_results(self, next_data: Dict[Any, Any], listing_type: str = 'sale') -> List[ScrapedProperty]:
        properties = []
        
        try:
            raw_listings = next_data.get("props", {}).get("pageProps", {}).get("listings", [])
            
            if not raw_listings:
                logger.warning("No listings found in __NEXT_DATA__")
                return []
            
            logger.info(f"Found {len(raw_listings)} listings in __NEXT_DATA__")
            
            for item in raw_listings:
                try:
                    listing_data = item.get("listing", {})
                    if listing_data:
                        wrapped_data = {"pageProps": {"listing": listing_data}}
                        property_data = self.parse_property_details_json(wrapped_data, listing_type)
                        if property_data:
                            properties.append(property_data)
                except Exception as e:
                    logger.error(f"Error parsing listing from __NEXT_DATA__: {str(e)}")
                    continue
            
            logger.info(f"Parsed {len(properties)} properties from __NEXT_DATA__")
            return properties
            
        except Exception as e:
            logger.error(f"Error parsing __NEXT_DATA__ search results: {str(e)}")
            return []
