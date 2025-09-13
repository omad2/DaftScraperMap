from typing import List, Optional, Literal
from loguru import logger
from config import config
from models import ScrapedProperty, PropertyListing
from core.fetcher import Fetcher
from core.parser import Parser
from core.supabase_client import SupabaseClient
from core.utils import delay, parse_bathrooms

class DaftScraper:
    def __init__(self):
        self.fetcher = Fetcher()
        self.parser = Parser()
        self.supabase_client = SupabaseClient()

    def build_search_url(self, listing_type: Literal['rent', 'sale'], location: str = "dublin") -> str:
        if listing_type == 'rent':
            base_path = "/property-for-rent"
        else:
            base_path = "/property-for-sale"
        
        if listing_type == 'rent':
            location_mapping = {
                "dublin": "dublin-city",
                "dublin-city": "dublin-city",
                "cork": "cork-city",
                "galway": "galway-city",
                "limerick": "limerick-city",
                "waterford": "waterford-city"
            }
        else:
            location_mapping = {
                "dublin": "dublin",
                "dublin-city": "dublin",
                "cork": "cork",
                "galway": "galway",
                "limerick": "limerick",
                "waterford": "waterford"
            }
        
        location_slug = location_mapping.get(location.lower(), "dublin" if listing_type == 'sale' else "dublin-city")
        url_path = f"{base_path}/{location_slug}"
        
        full_url = f"{config.DAFT_BASE_URL}{url_path}"
        logger.info(f"Constructed search URL: {full_url}")
        return full_url

    def scrape_all_pages(self, base_url: str, listing_type: Literal['rent', 'sale'], use_json_api: bool = True) -> List[ScrapedProperty]:
        current_page = 1
        total_pages = 1
        all_properties = []

        while current_page <= total_pages:
            try:
                if current_page > 1:
                    delay(1500)

                if use_json_api:
                    page_url = base_url
                    if current_page > 1:
                        separator = '&' if '?' in base_url else '?'
                        page_url = f"{base_url}{separator}page={current_page}"

                    html = self.fetcher.fetch_page_html(page_url, current_page)
                    if not html:
                        logger.warning(f"No HTML content for page {current_page}")
                        current_page += 1
                        continue

                    if current_page == 1:
                        total_pages = self.parser.get_total_pages(html)

                    properties_on_page = self.parser.parse_search_results(html)
                    
                    detailed_properties = []
                    for prop in properties_on_page:
                        if prop.url:
                            try:
                                delay(500)
                                
                                property_id, address_slug = self._extract_property_info_from_url(prop.url)
                                if property_id and address_slug:
                                    api_url = self.fetcher.build_property_api_url(property_id, address_slug)
                                    json_data = self.fetcher.fetch_json_api(api_url, 0)
                                    if json_data:
                                        enhanced_property = self.parser.parse_property_details_json(json_data, listing_type)
                                        if enhanced_property:
                                            detailed_properties.append(enhanced_property)
                                            continue
                                
                                detail_html = self.fetcher.fetch_page_html(prop.url, 0)
                                if detail_html:
                                    enhanced_property = self.parser.parse_property_details(detail_html, prop)
                                    detailed_properties.append(enhanced_property)
                                else:
                                    detailed_properties.append(prop)
                            except Exception as e:
                                logger.error(f"Error fetching details for {prop.url}: {str(e)}")
                                detailed_properties.append(prop)

                    all_properties.extend(detailed_properties)
                    logger.info(f"Page {current_page}: Found {len(detailed_properties)} properties (HTML + JSON API)")
                    
                else:
                    page_url = base_url
                    if current_page > 1:
                        separator = '&' if '?' in base_url else '?'
                        page_url = f"{base_url}{separator}page={current_page}"

                    html = self.fetcher.fetch_page_html(page_url, current_page)
                    if not html:
                        logger.warning(f"No HTML content for page {current_page}")
                        current_page += 1
                        continue

                    if current_page == 1:
                        total_pages = self.parser.get_total_pages(html)

                    properties_on_page = self.parser.parse_search_results(html)
                    
                    detailed_properties = []
                    for prop in properties_on_page:
                        if prop.url:
                            try:
                                delay(500)
                                
                                detail_html = self.fetcher.fetch_page_html(prop.url, 0)
                                if detail_html:
                                    enhanced_property = self.parser.parse_property_details(detail_html, prop)
                                    detailed_properties.append(enhanced_property)
                                else:
                                    detailed_properties.append(prop)
                            except Exception as e:
                                logger.error(f"Error fetching details for {prop.url}: {str(e)}")
                                detailed_properties.append(prop)

                    all_properties.extend(detailed_properties)
                    logger.info(f"Page {current_page}: Found {len(detailed_properties)} properties (HTML)")
                
                current_page += 1

            except Exception as e:
                logger.error(f"Error processing page {current_page}: {str(e)}")
                if use_json_api and current_page == 1:
                    logger.info("JSON API failed, falling back to HTML scraping")
                    return self.scrape_all_pages(base_url, listing_type, use_json_api=False)
                current_page += 1
                continue

        logger.info(f"Total properties scraped: {len(all_properties)}")
        return all_properties

    def get_property_count(self, listing_type: Literal['rent', 'sale'], location: str = "dublin") -> dict:
        logger.info(f"Getting property count for {listing_type} properties in {location}")
        
        try:
            if listing_type == 'rent':
                base_path = "/property-for-rent"
            else:
                base_path = "/property-for-sale"
            
            if listing_type == 'rent':
                location_mapping = {
                    "dublin": "dublin-city",
                    "dublin-city": "dublin-city",
                    "cork": "cork-city",
                    "galway": "galway-city",
                    "limerick": "limerick-city",
                    "waterford": "waterford-city"
                }
            else:
                location_mapping = {
                    "dublin": "dublin",
                    "dublin-city": "dublin",
                    "cork": "cork",
                    "galway": "galway",
                    "limerick": "limerick",
                    "waterford": "waterford"
                }
            
            location_slug = location_mapping.get(location.lower(), "dublin" if listing_type == 'sale' else "dublin-city")
            search_path = f"{base_path}/{location_slug}"
            
            logger.info(f"Constructed search path: {search_path}")
            
            next_data = self.fetcher.fetch_search_results_json(search_path, 1)
            
            if not next_data:
                logger.warning(f"No __NEXT_DATA__ content for {listing_type} properties")
                return {"success": False, "count": 0, "message": "Failed to fetch property count"}
            
            properties = self.parser.parse_next_data_search_results(next_data, listing_type)
            
            paging = next_data.get("props", {}).get("pageProps", {}).get("paging", {})
            total_results = paging.get("totalResults", 0)
            
            if total_results > 0:
                total_properties = total_results
                properties_per_page = paging.get("pageSize", 20)
                total_pages = paging.get("totalPages", 1)
            else:
                total_properties = len(properties)
                properties_per_page = 20
                total_pages = 1
            
            logger.info(f"Found {len(properties)} {listing_type} properties in {location} (total: {total_properties})")
            
            return {
                "success": True,
                "count": total_properties,
                "pages": total_pages,
                "properties_per_page": properties_per_page,
                "message": f"Found {total_properties} {listing_type} properties"
            }
            
        except Exception as e:
            logger.error(f"Error getting property count: {str(e)}")
            return {"success": False, "count": 0, "message": str(e)}

    def scrape_limited_pages(self, base_url: str, listing_type: Literal['rent', 'sale'], max_properties: int) -> List[ScrapedProperty]:
        logger.info(f"Scraping up to {max_properties} {listing_type} properties")
        
        current_page = 1
        total_pages = 1
        all_properties = []
        properties_scraped = 0

        while current_page <= total_pages and properties_scraped < max_properties:
            try:
                if current_page > 1:
                    delay(1500)

                search_path = base_url.replace(config.DAFT_BASE_URL, "")
                
                next_data = self.fetcher.fetch_search_results_json(search_path, current_page)
                if not next_data:
                    logger.warning(f"No __NEXT_DATA__ content for page {current_page}")
                    current_page += 1
                    continue

                if current_page == 1:
                    paging = next_data.get("props", {}).get("pageProps", {}).get("paging", {})
                    total_results = paging.get("totalResults", 0)
                    properties_per_page = paging.get("pageSize", 20)
                    if total_results > 0:
                        total_pages = paging.get("totalPages", 1)
                    else:
                        total_pages = 1

                properties_on_page = self.parser.parse_next_data_search_results(next_data, listing_type)
                
                remaining_properties = max_properties - properties_scraped
                if len(properties_on_page) > remaining_properties:
                    properties_on_page = properties_on_page[:remaining_properties]
                
                detailed_properties = []
                for prop in properties_on_page:
                    if prop.url and properties_scraped < max_properties:
                        try:
                            delay(500)
                            
                            property_id, address_slug = self._extract_property_info_from_url(prop.url)
                            if property_id and address_slug:
                                api_url = self.fetcher.build_property_api_url(property_id, address_slug)
                                json_data = self.fetcher.fetch_json_api(api_url, 0)
                                if json_data:
                                    enhanced_property = self.parser.parse_property_details_json(json_data, listing_type)
                                    if enhanced_property:
                                        detailed_properties.append(enhanced_property)
                                        properties_scraped += 1
                                        continue
                            
                            detail_html = self.fetcher.fetch_page_html(prop.url, 0)
                            if detail_html:
                                enhanced_property = self.parser.parse_property_details(detail_html, prop)
                                detailed_properties.append(enhanced_property)
                                properties_scraped += 1
                            else:
                                detailed_properties.append(prop)
                                properties_scraped += 1
                        except Exception as e:
                            logger.error(f"Error fetching details for {prop.url}: {str(e)}")
                            detailed_properties.append(prop)
                            properties_scraped += 1

                all_properties.extend(detailed_properties)
                logger.info(f"Page {current_page}: Found {len(detailed_properties)} properties (Total scraped: {properties_scraped})")
                
                current_page += 1

            except Exception as e:
                logger.error(f"Error processing page {current_page}: {str(e)}")
                current_page += 1
                continue

        logger.info(f"Total properties scraped: {len(all_properties)}")
        return all_properties

    def _extract_property_info_from_url(self, url: str) -> tuple:
        try:
            
            if config.DAFT_BASE_URL in url:
                relative_url = url.replace(config.DAFT_BASE_URL, '')
            else:
                relative_url = url
            
            url_parts = relative_url.strip('/').split('/')
            if len(url_parts) >= 3:
                property_id = url_parts[-1]
                address_slug = url_parts[-2]
                
                if property_id.isdigit():
                    return property_id, address_slug
            
            return None, None
            
        except Exception as e:
            logger.error(f"Error extracting property info from URL {url}: {str(e)}")
            return None, None

    def transform_to_property_listing(self, scraped_prop: ScrapedProperty, listing_type: Literal['rent', 'sale']) -> PropertyListing:
        price_period = None
        if scraped_prop.price_string:
            price_lower = scraped_prop.price_string.lower()
            if 'week' in price_lower or 'pw' in price_lower:
                price_period = 'week'
            elif 'month' in price_lower or 'pm' in price_lower:
                price_period = 'month'

        bathrooms = parse_bathrooms(scraped_prop.baths_string)

        title = scraped_prop.tagline if scraped_prop.tagline else scraped_prop.address

        return PropertyListing(
            id=int(scraped_prop.id) if scraped_prop.id and scraped_prop.id.isdigit() else None,
            url=scraped_prop.url,
            title=title,
            listing_type=listing_type,
            price_eur=scraped_prop.parsed_price,
            price_period=price_period,
            bedrooms=scraped_prop.parsed_beds.min if scraped_prop.parsed_beds else None,
            bathrooms=bathrooms,
            property_type=scraped_prop.property_type_string,
            latitude=scraped_prop.latitude,
            longitude=scraped_prop.longitude,
            date_listed=scraped_prop.date_listed,
            image_url=scraped_prop.image_url,
            address_full=scraped_prop.address
        )

    def scrape_and_upload(self, listing_type: Literal['rent', 'sale'] = 'rent', location: str = "dublin") -> dict:
        logger.info(f"Starting scrape for {listing_type} properties in {location}")
        
        try:
            search_url = self.build_search_url(listing_type, location)
            
            scraped_properties = self.scrape_all_pages(search_url, listing_type)
            
            if not scraped_properties:
                logger.warning("No properties found")
                return {"success": False, "message": "No properties found", "count": 0}
            
            property_listings = []
            for scraped_prop in scraped_properties:
                try:
                    listing = self.transform_to_property_listing(scraped_prop, listing_type)
                    property_listings.append(listing)
                except Exception as e:
                    logger.error(f"Error transforming property {scraped_prop.url}: {str(e)}")
                    continue
            
            logger.info(f"Transformed {len(property_listings)} properties")
            
            existing_ids = self.supabase_client.get_existing_property_ids()
            logger.info(f"Found {len(existing_ids)} existing properties in database")
            
            new_properties = [prop for prop in property_listings if prop.id not in existing_ids]
            logger.info(f"Found {len(new_properties)} new properties to insert")
            
            if not new_properties:
                logger.info("No new properties to insert")
                return {"success": True, "message": "No new properties to insert", "count": 0}
            
            batch_size = 100
            total_inserted = 0
            
            for i in range(0, len(new_properties), batch_size):
                batch = new_properties[i:i + batch_size]
                try:
                    result = self.supabase_client.upsert_properties_batch(batch)
                    total_inserted += len(result)
                    logger.info(f"Upserted batch {i//batch_size + 1}: {len(result)} properties")
                except Exception as e:
                    logger.error(f"Error upserting batch {i//batch_size + 1}: {str(e)}")
                    continue
            
            logger.info(f"Successfully scraped and uploaded {total_inserted} properties")
            return {
                "success": True, 
                "message": f"Successfully scraped and uploaded {total_inserted} properties",
                "count": total_inserted
            }
            
        except Exception as e:
            logger.error(f"Error in scrape_and_upload: {str(e)}")
            return {"success": False, "message": str(e), "count": 0}
        
        finally:
            self.fetcher.close()

    def scrape_both_rent_and_sale(self, location: str = "dublin") -> dict:
        logger.info(f"Starting scrape for both rent and sale properties in {location}")
        
        results = {}
        
        logger.info("Scraping rent properties...")
        rent_result = self.scrape_and_upload('rent', location)
        results['rent'] = rent_result
        
        logger.info("Scraping sale properties...")
        sale_result = self.scrape_and_upload('sale', location)
        results['sale'] = sale_result
        
        total_count = rent_result.get('count', 0) + sale_result.get('count', 0)
        
        logger.info(f"Total properties scraped: {total_count} (Rent: {rent_result.get('count', 0)}, Sale: {sale_result.get('count', 0)})")
        
        return {
            "success": True,
            "message": f"Scraped {total_count} total properties",
            "count": total_count,
            "details": results
        }

    def interactive_scrape(self, location: str = "dublin") -> dict:
        logger.info(f"Starting interactive scrape for {location}")
        
        print(f"\nDaft.ie Property Scraper for {location.title()}")
        print("=" * 50)
        
        try:
            print("\nGetting property counts...")
            
            rent_count_result = self.get_property_count('rent', location)
            sale_count_result = self.get_property_count('sale', location)
            
            if not rent_count_result["success"] or not sale_count_result["success"]:
                print("Failed to get property counts. Please check your internet connection.")
                return {"success": False, "message": "Failed to get property counts"}
            
            rent_count = rent_count_result["count"]
            sale_count = sale_count_result["count"]
            
            print(f"\nAvailable Properties in {location.title()}:")
            print(f"   For Sale: {sale_count:,} properties")
            print(f"   For Rent: {rent_count:,} properties")
            print(f"   Total: {rent_count + sale_count:,} properties")
            
            sale_pages = (sale_count + 19) // 20
            rent_pages = (rent_count + 19) // 20
            
            print(f"\nPages available:")
            print(f"   For Sale: {sale_pages:,} pages ({sale_count:,} properties)")
            print(f"   For Rent: {rent_pages:,} pages ({rent_count:,} properties)")
            
            print(f"\nHow many pages would you like to scrape?")
            
            while True:
                try:
                    sale_input = input(f"   For Sale (0-{sale_pages:,}): ").strip()
                    if sale_input.lower() == 'all':
                        max_sale_pages = sale_pages
                        break
                    elif sale_input == '0':
                        max_sale_pages = 0
                        break
                    else:
                        max_sale_pages = int(sale_input)
                        if 0 <= max_sale_pages <= sale_pages:
                            break
                        else:
                            print(f"   Please enter a number between 0 and {sale_pages:,}")
                except ValueError:
                    print("   Please enter a valid number or 'all'")
            
            while True:
                try:
                    rent_input = input(f"   For Rent (0-{rent_pages:,}): ").strip()
                    if rent_input.lower() == 'all':
                        max_rent_pages = rent_pages
                        break
                    elif rent_input == '0':
                        max_rent_pages = 0
                        break
                    else:
                        max_rent_pages = int(rent_input)
                        if 0 <= max_rent_pages <= rent_pages:
                            break
                        else:
                            print(f"   Please enter a number between 0 and {rent_pages:,}")
                except ValueError:
                    print("   Please enter a valid number or 'all'")
            
            total_pages_to_scrape = max_sale_pages + max_rent_pages
            print(f"\nScraping Plan:")
            print(f"   Sale Pages: {max_sale_pages:,} (up to {max_sale_pages * 20:,} properties)")
            print(f"   Rent Pages: {max_rent_pages:,} (up to {max_rent_pages * 20:,} properties)")
            print(f"   Total Pages: {total_pages_to_scrape:,}")
            
            if total_pages_to_scrape == 0:
                print("No properties selected for scraping.")
                return {"success": False, "message": "No properties selected"}
            
            confirm = input(f"\nStart scraping? (y/n): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("Scraping cancelled.")
                return {"success": False, "message": "Scraping cancelled by user"}
            
            print(f"\nStarting scraping process...")
            results = {}
            total_inserted = 0
            
            if max_sale_pages > 0:
                print(f"\nScraping {max_sale_pages:,} sale pages...")
                sale_result = self.scrape_limited_and_upload('sale', location, max_sale_pages)
                results['sale'] = sale_result
                total_inserted += sale_result.get('count', 0)
                print(f"Sale scraping completed: {sale_result.get('count', 0)} properties uploaded")
            
            if max_rent_pages > 0:
                print(f"\nScraping {max_rent_pages:,} rent pages...")
                rent_result = self.scrape_limited_and_upload('rent', location, max_rent_pages)
                results['rent'] = rent_result
                total_inserted += rent_result.get('count', 0)
                print(f"Rent scraping completed: {rent_result.get('count', 0)} properties uploaded")
            
            print(f"\nScraping Complete!")
            print(f"   Total Properties Uploaded: {total_inserted:,}")
            print(f"   Sale Properties: {results.get('sale', {}).get('count', 0):,}")
            print(f"   Rent Properties: {results.get('rent', {}).get('count', 0):,}")
            
            return {
                "success": True,
                "message": f"Successfully scraped and uploaded {total_inserted} properties",
                "count": total_inserted,
                "details": results
            }
            
        except KeyboardInterrupt:
            print("\nScraping interrupted by user.")
            return {"success": False, "message": "Scraping interrupted by user"}
        except Exception as e:
            logger.error(f"Error in interactive scrape: {str(e)}")
            print(f"Error during scraping: {str(e)}")
            return {"success": False, "message": str(e)}
        finally:
            self.fetcher.close()

    def scrape_limited_and_upload(self, listing_type: Literal['rent', 'sale'], location: str, max_pages: int) -> dict:
        logger.info(f"Starting page-based scrape for first {max_pages} pages of {listing_type} properties in {location}")
        
        try:
            search_url = self.build_search_url(listing_type, location)
            
            existing_ids = self.supabase_client.get_existing_property_ids()
            logger.info(f"Found {len(existing_ids)} existing properties in database")
            
            new_properties = []
            processed_property_ids = set()
            current_page = 1
            
            while current_page <= max_pages:
                try:
                    if current_page > 1:
                        delay(1500)

                    search_path = search_url.replace(config.DAFT_BASE_URL, "")
                    
                    next_data = self.fetcher.fetch_search_results_json(search_path, current_page)
                    if not next_data:
                        logger.warning(f"No __NEXT_DATA__ content for page {current_page}")
                        current_page += 1
                        continue

                    if current_page == 1:
                        paging = next_data.get("props", {}).get("pageProps", {}).get("paging", {})
                        total_results = paging.get("totalResults", 0)
                        total_pages_available = paging.get("totalPages", 1)
                        logger.info(f"Total available: {total_results} properties across {total_pages_available} pages")

                    properties_on_page = self.parser.parse_next_data_search_results(next_data, listing_type)
                    
                    if not properties_on_page:
                        logger.warning(f"No properties found on page {current_page}")
                        current_page += 1
                        continue
                    
                    logger.info(f"Page {current_page}: Found {len(properties_on_page)} properties")
                    
                    new_properties_on_this_page = 0
                    for prop in properties_on_page:
                        if prop.id and prop.id in processed_property_ids:
                            logger.debug(f"Skipping already processed property ID: {prop.id}")
                            continue
                            
                        if prop.id and prop.id in existing_ids:
                            logger.debug(f"Skipping existing property ID: {prop.id}")
                            continue
                        
                        logger.info(f"Processing new property: {prop.url}")
                            
                        try:
                            delay(500)
                            
                            property_id, address_slug = self._extract_property_info_from_url(prop.url)
                            if property_id and address_slug:
                                api_url = self.fetcher.build_property_api_url(property_id, address_slug)
                                json_data = self.fetcher.fetch_json_api(api_url, 0)
                                if json_data:
                                    enhanced_property = self.parser.parse_property_details_json(json_data, listing_type)
                                    if enhanced_property:
                                        listing = self.transform_to_property_listing(enhanced_property, listing_type)
                                        
                                        if listing.id and listing.id not in existing_ids and listing.id not in processed_property_ids:
                                            new_properties.append(listing)
                                            processed_property_ids.add(listing.id)
                                            new_properties_on_this_page += 1
                                            logger.info(f"Found new property {len(new_properties)}: {prop.url}")
                                        else:
                                            logger.debug(f"Skipping duplicate property ID: {listing.id}")
                                        continue
                            
                            detail_html = self.fetcher.fetch_page_html(prop.url, 0)
                            if detail_html:
                                enhanced_property = self.parser.parse_property_details(detail_html, prop)
                                if enhanced_property:
                                    listing = self.transform_to_property_listing(enhanced_property, listing_type)
                                    
                                    if listing.id and listing.id not in existing_ids and listing.id not in processed_property_ids:
                                        new_properties.append(listing)
                                        processed_property_ids.add(listing.id)
                                        new_properties_on_this_page += 1
                                        logger.info(f"Found new property {len(new_properties)}: {prop.url}")
                                    else:
                                        logger.debug(f"Skipping duplicate property ID: {listing.id}")
                        except Exception as e:
                            logger.error(f"Error processing property {prop.url}: {str(e)}")
                            try:
                                listing = self.transform_to_property_listing(prop, listing_type)
                                
                                if listing.id and listing.id not in existing_ids and listing.id not in processed_property_ids:
                                    new_properties.append(listing)
                                    processed_property_ids.add(listing.id)
                                    new_properties_on_this_page += 1
                                    logger.info(f"Found new property (fallback) {len(new_properties)}: {prop.url}")
                                else:
                                    logger.debug(f"Skipping duplicate property ID (fallback): {listing.id}")
                            except Exception as fallback_error:
                                logger.error(f"Fallback processing also failed for {prop.url}: {str(fallback_error)}")
                                continue
                    
                    logger.info(f"Page {current_page} completed: {new_properties_on_this_page} new properties found")
                    current_page += 1
                    
                except Exception as e:
                    logger.error(f"Error processing page {current_page}: {str(e)}")
                    current_page += 1
                    continue
            
            logger.info(f"Found {len(new_properties)} new properties after checking {current_page - 1} pages")
            
            if not new_properties:
                logger.info("No new properties to insert")
                return {"success": True, "message": "No new properties to insert", "count": 0}
            
            batch_size = 100
            total_inserted = 0
            
            for i in range(0, len(new_properties), batch_size):
                batch = new_properties[i:i + batch_size]
                try:
                    result = self.supabase_client.upsert_properties_batch(batch)
                    total_inserted += len(result)
                    logger.info(f"Upserted batch {i//batch_size + 1}: {len(result)} properties")
                except Exception as e:
                    logger.error(f"Error upserting batch {i//batch_size + 1}: {str(e)}")
                    continue
            
            logger.info(f"Successfully scraped and uploaded {total_inserted} NEW properties")
            return {
                "success": True, 
                "message": f"Successfully scraped and uploaded {total_inserted} NEW properties",
                "count": total_inserted
            }
            
        except Exception as e:
            logger.error(f"Error in scrape_limited_and_upload: {str(e)}")
            return {"success": False, "message": str(e), "count": 0}
