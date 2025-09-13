from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from decimal import Decimal

class PropertyListing(BaseModel):
    """Model for property listing data that matches the Supabase schema"""
    id: Optional[int] = None
    url: str
    title: str
    listing_type: Literal['rent', 'sale']
    price_eur: Optional[Decimal] = None
    price_period: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    property_type: Optional[str] = None
    size_sqm: Optional[Decimal] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    date_listed: Optional[datetime] = None
    image_url: Optional[str] = None
    address_full: Optional[str] = None
    inserted_at: Optional[datetime] = Field(default_factory=datetime.now)

class ParsedPriceResult(BaseModel):
    value: Optional[float] = None
    type: Literal['numeric', 'on_application', 'unknown'] = 'unknown'

class ParsedBedsResult(BaseModel):
    min: int
    max: int
    is_studio: Optional[bool] = False

class ScrapedProperty(BaseModel):
    """Model for raw scraped property data before transformation"""
    address: str
    url: str
    id: str
    tagline: str
    price_string: str
    parsed_price: Optional[float] = None
    price_type: Literal['numeric', 'on_application', 'unknown'] = 'unknown'
    beds_string: str
    parsed_beds: Optional[ParsedBedsResult] = None
    baths_string: str
    property_type_string: str
    ber: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_url: Optional[str] = None
    date_listed: Optional[datetime] = None
