from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime
from decimal import Decimal
import re
from urllib.parse import urlparse

class ScrapingRequest(BaseModel):
    """Request model for scraping operations"""
    listing_type: Literal['rent', 'sale', 'both'] = Field(..., description="Type of properties to scrape")
    location: str = Field(default="dublin", description="Location to scrape")
    max_properties: Optional[int] = Field(default=None, ge=1, le=1000, description="Maximum properties to scrape")
    use_json_api: bool = Field(default=True, description="Whether to use JSON API for scraping")
    
    @field_validator('location')
    @classmethod
    def validate_location(cls, v):
        """Validate location parameter"""
        valid_locations = [
            'dublin', 'dublin-city', 'cork', 'cork-city', 
            'galway', 'galway-city', 'limerick', 'limerick-city',
            'waterford', 'waterford-city'
        ]
        if v.lower() not in valid_locations:
            raise ValueError(f"Invalid location. Must be one of: {', '.join(valid_locations)}")
        return v.lower()
    
    @field_validator('max_properties')
    @classmethod
    def validate_limits(cls, v):
        """Validate numeric limits"""
        if v is not None and v <= 0:
            raise ValueError("Limit must be greater than 0")
        return v

class PropertyQueryRequest(BaseModel):
    """Request model for property queries"""
    listing_type: Optional[Literal['rent', 'sale']] = Field(default=None, description="Filter by listing type")
    location: Optional[str] = Field(default=None, description="Filter by location")
    min_price: Optional[Decimal] = Field(default=None, ge=0, description="Minimum price filter")
    max_price: Optional[Decimal] = Field(default=None, ge=0, description="Maximum price filter")
    min_bedrooms: Optional[int] = Field(default=None, ge=0, le=10, description="Minimum bedrooms")
    max_bedrooms: Optional[int] = Field(default=None, ge=0, le=10, description="Maximum bedrooms")
    min_bathrooms: Optional[int] = Field(default=None, ge=0, le=10, description="Minimum bathrooms")
    property_type: Optional[str] = Field(default=None, description="Filter by property type")
    limit: int = Field(default=20, ge=1, le=100, description="Number of results to return")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
    sort_by: Optional[Literal['price_eur', 'date_listed', 'bedrooms', 'bathrooms']] = Field(
        default='date_listed', description="Field to sort by"
    )
    sort_order: Literal['asc', 'desc'] = Field(default='desc', description="Sort order")
    
    @model_validator(mode='after')
    def validate_ranges(self):
        """Validate price and room ranges"""
        if self.max_price is not None and self.min_price is not None:
            if self.max_price < self.min_price:
                raise ValueError("max_price must be greater than or equal to min_price")
        
        if self.max_bedrooms is not None and self.min_bedrooms is not None:
            if self.max_bedrooms < self.min_bedrooms:
                raise ValueError("max_bedrooms must be greater than or equal to min_bedrooms")
        
        if self.max_bathrooms is not None and self.min_bathrooms is not None:
            if self.max_bathrooms < self.min_bathrooms:
                raise ValueError("max_bathrooms must be greater than or equal to min_bathrooms")
        
        return self

class PropertyUpdateRequest(BaseModel):
    """Request model for updating properties"""
    title: Optional[str] = Field(default=None, min_length=1, max_length=500, description="Property title")
    price_eur: Optional[Decimal] = Field(default=None, ge=0, description="Price in EUR")
    price_period: Optional[Literal['week', 'month', 'year']] = Field(default=None, description="Price period")
    bedrooms: Optional[int] = Field(default=None, ge=0, le=10, description="Number of bedrooms")
    bathrooms: Optional[int] = Field(default=None, ge=0, le=10, description="Number of bathrooms")
    property_type: Optional[str] = Field(default=None, max_length=100, description="Property type")
    size_sqm: Optional[Decimal] = Field(default=None, ge=0, description="Size in square meters")
    latitude: Optional[Decimal] = Field(default=None, ge=-90, le=90, description="Latitude")
    longitude: Optional[Decimal] = Field(default=None, ge=-180, le=180, description="Longitude")
    image_url: Optional[str] = Field(default=None, description="Image URL")
    address_full: Optional[str] = Field(default=None, max_length=500, description="Full address")
    
    @field_validator('image_url')
    @classmethod
    def validate_image_url(cls, v):
        """Validate image URL format"""
        if v is not None:
            parsed = urlparse(v)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
            if not any(v.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                raise ValueError("URL must point to an image file")
        return v

class PropertyResponse(BaseModel):
    """Response model for property data"""
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
    inserted_at: Optional[datetime] = None

class ScrapingResponse(BaseModel):
    """Response model for scraping operations"""
    success: bool
    message: str
    count: int = 0
    details: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    errors: Optional[List[str]] = None

class PropertyListResponse(BaseModel):
    """Response model for property list queries"""
    properties: List[PropertyResponse]
    total_count: int
    limit: int
    offset: int
    has_more: bool

class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: Literal['healthy', 'unhealthy']
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    services: Dict[str, str] = Field(default_factory=dict)

class StatisticsResponse(BaseModel):
    """Statistics response model"""
    total_properties: int
    rent_properties: int
    sale_properties: int
    properties_by_location: Dict[str, int]
    properties_by_type: Dict[str, int]
    average_price_rent: Optional[Decimal] = None
    average_price_sale: Optional[Decimal] = None
    last_updated: Optional[datetime] = None

def validate_daft_url(url: str) -> bool:
    """Validate that URL is a valid Daft.ie property URL"""
    if not url:
        return False
    
    try:
        parsed = urlparse(url)
        if parsed.netloc not in ['www.daft.ie', 'daft.ie']:
            return False
        
        # Check if it's a property URL (contains /for-rent/ or /for-sale/)
        path = parsed.path.lower()
        if not ('/for-rent/' in path or '/for-sale/' in path):
            return False
        
        return True
    except Exception:
        return False

def validate_coordinates(lat: float, lon: float) -> bool:
    """Validate latitude and longitude coordinates"""
    return -90 <= lat <= 90 and -180 <= lon <= 180

def validate_price_string(price_str: str) -> bool:
    """Validate price string format"""
    if not price_str:
        return False
    
    # Remove common currency symbols and whitespace
    cleaned = re.sub(r'[€$£,\s]', '', price_str.lower())
    
    # Check for common patterns
    patterns = [
        r'^\d+$',  # Just numbers
        r'^\d+\.\d+$',  # Decimal numbers
        r'^\d+k$',  # Numbers with k suffix
        r'^\d+\.\d+k$',  # Decimal with k suffix
        r'^on\s*application$',  # On application
        r'^poa$',  # Price on application
        r'^contact\s*agent$',  # Contact agent
    ]
    
    return any(re.match(pattern, cleaned) for pattern in patterns)
