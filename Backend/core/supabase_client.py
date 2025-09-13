from typing import List, Optional
from supabase import create_client, Client
from loguru import logger
from config import config
from models import PropertyListing
from decimal import Decimal
from datetime import datetime
import json
from exceptions import DatabaseException, ConfigurationException


class SupabaseClient:
    def __init__(self):
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise ConfigurationException(
                "SUPABASE_URL and SUPABASE_KEY must be set in environment variables",
                config_key="SUPABASE_URL/SUPABASE_KEY"
            )
        
        try:
            self.client: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
            self.table_name = "listings"
        except Exception as e:
            logger.error(f"Failed to create Supabase client: {str(e)}")
            raise DatabaseException(
                f"Failed to create Supabase client: {str(e)}",
                operation="init",
                details={"url": config.SUPABASE_URL, "error": str(e)}
            )

    def insert_property(self, property_data: PropertyListing) -> Optional[dict]:
        """Insert a single property listing"""
        try:
            # Convert to dict and handle None values
            data = property_data.model_dump(exclude_none=True)
            
            # Remove id if it's None (let Supabase auto-generate)
            if data.get('id') is None:
                data.pop('id', None)
            
            result = self.client.table(self.table_name).insert(data).execute()
            
            if result.data:
                logger.info(f"Successfully inserted property: {property_data.url}")
                return result.data[0]
            else:
                logger.error(f"Failed to insert property: {property_data.url}")
                return None
                
        except Exception as e:
            logger.error(f"Error inserting property {property_data.url}: {str(e)}")
            raise DatabaseException(
                f"Failed to insert property: {str(e)}",
                operation="insert",
                table=self.table_name,
                details={"url": property_data.url, "error": str(e)}
            )

    def insert_properties_batch(self, properties: List[PropertyListing]) -> List[dict]:
        """Insert multiple property listings in batch"""
        if not properties:
            return []
        
        try:
            # Convert to list of dicts and handle None values
            data_list = []
            for prop in properties:
                data = prop.model_dump()
                # Remove id if it's None (let Supabase auto-generate)
                if data.get('id') is None:
                    data.pop('id', None)
                
                # Convert Decimal to float for JSON serialization
                for key, value in data.items():
                    if isinstance(value, Decimal):
                        data[key] = float(value)
                    elif isinstance(value, datetime):
                        data[key] = value.isoformat()
                
                data_list.append(data)
            
            result = self.client.table(self.table_name).insert(data_list).execute()
            
            if result.data:
                logger.info(f"Successfully inserted {len(result.data)} properties in batch")
                return result.data
            else:
                logger.error("Failed to insert properties in batch")
                return []
                
        except Exception as e:
            logger.error(f"Error inserting properties in batch: {str(e)}")
            raise DatabaseException(
                f"Failed to insert properties in batch: {str(e)}",
                operation="batch_insert",
                table=self.table_name,
                details={"count": len(properties), "error": str(e)}
            )

    def get_existing_property_ids(self) -> set:
        """Get set of existing property IDs to avoid duplicates"""
        try:
            result = self.client.table(self.table_name).select("id").execute()
            if result.data:
                return {prop['id'] for prop in result.data if prop['id'] is not None}
            return set()
        except Exception as e:
            logger.error(f"Error fetching existing property IDs: {str(e)}")
            raise DatabaseException(
                f"Failed to fetch existing property IDs: {str(e)}",
                operation="select",
                table=self.table_name,
                details={"error": str(e)}
            )
    
    def get_existing_property_urls(self) -> set:
        """Get set of existing property URLs to avoid duplicates (legacy method)"""
        try:
            result = self.client.table(self.table_name).select("url").execute()
            if result.data:
                return {prop['url'] for prop in result.data}
            return set()
        except Exception as e:
            logger.error(f"Error fetching existing property URLs: {str(e)}")
            raise DatabaseException(
                f"Failed to fetch existing property URLs: {str(e)}",
                operation="select",
                table=self.table_name,
                details={"error": str(e)}
            )

    def upsert_property(self, property_data: PropertyListing) -> Optional[dict]:
        """Upsert (insert or update) a property listing based on URL"""
        try:
            data = property_data.model_dump(exclude_none=True)
            
            # Remove id if it's None (let Supabase auto-generate)
            if data.get('id') is None:
                data.pop('id', None)
            
            # Convert Decimal objects to float and datetime objects to ISO strings for JSON serialization
            for key, value in data.items():
                if isinstance(value, Decimal):
                    data[key] = float(value)
                elif isinstance(value, datetime):
                    data[key] = value.isoformat()
            
            result = self.client.table(self.table_name).upsert(
                data, 
                on_conflict="id"
            ).execute()
            
            if result.data:
                logger.info(f"Successfully upserted property: {property_data.url}")
                return result.data[0]
            else:
                logger.error(f"Failed to upsert property: {property_data.url}")
                return None
                
        except Exception as e:
            logger.error(f"Error upserting property {property_data.url}: {str(e)}")
            raise DatabaseException(
                f"Failed to upsert property: {str(e)}",
                operation="upsert",
                table=self.table_name,
                details={"url": property_data.url, "error": str(e)}
            )

    def upsert_properties_batch(self, properties: List[PropertyListing]) -> List[dict]:
        """Upsert multiple property listings in batch"""
        if not properties:
            return []
        
        try:
            # Convert to list of dicts and handle None values
            data_list = []
            seen_ids = set()  # Track IDs to avoid duplicates within the batch
            
            for prop in properties:
                data = prop.model_dump()
                # Remove id if it's None (let Supabase auto-generate)
                if data.get('id') is None:
                    data.pop('id', None)
                
                # Skip if we've already seen this ID in this batch
                if data.get('id') and data['id'] in seen_ids:
                    logger.debug(f"Skipping duplicate ID {data['id']} within batch")
                    continue
                
                if data.get('id'):
                    seen_ids.add(data['id'])
                
                # Convert Decimal objects to float and datetime objects to ISO strings for JSON serialization
                for key, value in data.items():
                    if isinstance(value, Decimal):
                        data[key] = float(value)
                    elif isinstance(value, datetime):
                        data[key] = value.isoformat()
                
                data_list.append(data)
            
            logger.info(f"Attempting to upsert {len(data_list)} properties")
            logger.debug(f"Sample property data: {data_list[0] if data_list else 'No data'}")
            
            result = self.client.table(self.table_name).upsert(
                data_list, 
                on_conflict="id"
            ).execute()
            
            logger.info(f"Upsert result: {result}")
            
            if result.data:
                logger.info(f"Successfully upserted {len(result.data)} properties in batch")
                return result.data
            else:
                logger.error("Failed to upsert properties in batch")
                return []
                
        except Exception as e:
            logger.error(f"Error upserting properties in batch: {str(e)}")
            raise DatabaseException(
                f"Failed to upsert properties in batch: {str(e)}",
                operation="batch_upsert",
                table=self.table_name,
                details={"count": len(properties), "error": str(e)}
            )
