"""
FastAPI REST API for DublinMap property scraping and management
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
from loguru import logger

from validation import (
    ScrapingRequest, PropertyQueryRequest, PropertyUpdateRequest,
    PropertyResponse, ScrapingResponse, PropertyListResponse,
    ErrorResponse, HealthCheckResponse, StatisticsResponse
)
from exceptions import (
    DublinMapException, ScrapingException, ValidationException,
    DatabaseException, ConfigurationException, RateLimitException, NetworkException
)
from core import DaftScraper, SupabaseClient
from config import config

# Global variables for application state
scraper_instance: Optional[DaftScraper] = None
supabase_client: Optional[SupabaseClient] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global scraper_instance, supabase_client
    
    # Startup
    logger.info("Starting DublinMap API...")
    try:
        # Initialize Supabase client
        supabase_client = SupabaseClient()
        logger.info("Supabase client initialized successfully")
        
        # Initialize scraper
        scraper_instance = DaftScraper()
        logger.info("Daft scraper initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down DublinMap API...")
    if scraper_instance:
        scraper_instance.fetcher.close()
    logger.info("Cleanup completed")

# Create FastAPI app
app = FastAPI(
    title="DublinMap API",
    description="REST API for Dublin property scraping and management",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Dependency to get scraper instance
def get_scraper() -> DaftScraper:
    if scraper_instance is None:
        raise HTTPException(status_code=503, detail="Scraper service not available")
    return scraper_instance

# Dependency to get Supabase client
def get_supabase_client() -> SupabaseClient:
    if supabase_client is None:
        raise HTTPException(status_code=503, detail="Database service not available")
    return supabase_client

# Global exception handler
@app.exception_handler(DublinMapException)
async def dublin_map_exception_handler(request, exc: DublinMapException):
    """Handle custom DublinMap exceptions"""
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error=exc.error_code or "DUBLIN_MAP_ERROR",
            error_code=exc.error_code or "DUBLIN_MAP_ERROR",
            message=exc.message,
            details=exc.details
        ).model_dump()
    )

@app.exception_handler(ScrapingException)
async def scraping_exception_handler(request, exc: ScrapingException):
    """Handle scraping exceptions"""
    status_code = 502 if exc.status_code and exc.status_code >= 500 else 400
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error="SCRAPING_ERROR",
            error_code="SCRAPING_ERROR",
            message=exc.message,
            details={
                "url": exc.url,
                "status_code": exc.status_code,
                **exc.details
            }
        ).model_dump()
    )

@app.exception_handler(ValidationException)
async def validation_exception_handler(request, exc: ValidationException):
    """Handle validation exceptions"""
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="VALIDATION_ERROR",
            error_code="VALIDATION_ERROR",
            message=exc.message,
            details={
                "field": exc.field,
                "value": exc.value,
                **exc.details
            }
        ).model_dump()
    )

@app.exception_handler(DatabaseException)
async def database_exception_handler(request, exc: DatabaseException):
    """Handle database exceptions"""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="DATABASE_ERROR",
            error_code="DATABASE_ERROR",
            message=exc.message,
            details={
                "operation": exc.operation,
                "table": exc.table,
                **exc.details
            }
        ).model_dump()
    )

@app.exception_handler(ConfigurationException)
async def configuration_exception_handler(request, exc: ConfigurationException):
    """Handle configuration exceptions"""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="CONFIG_ERROR",
            error_code="CONFIG_ERROR",
            message=exc.message,
            details={
                "config_key": exc.config_key,
                **exc.details
            }
        ).model_dump()
    )

@app.exception_handler(RateLimitException)
async def rate_limit_exception_handler(request, exc: RateLimitException):
    """Handle rate limit exceptions"""
    headers = {}
    if exc.retry_after:
        headers["Retry-After"] = str(exc.retry_after)
    
    return JSONResponse(
        status_code=429,
        headers=headers,
        content=ErrorResponse(
            error="RATE_LIMIT_ERROR",
            error_code="RATE_LIMIT_ERROR",
            message=exc.message,
            details={
                "retry_after": exc.retry_after,
                **exc.details
            }
        ).model_dump()
    )

@app.exception_handler(NetworkException)
async def network_exception_handler(request, exc: NetworkException):
    """Handle network exceptions"""
    status_code = 504 if exc.timeout else 502
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error="NETWORK_ERROR",
            error_code="NETWORK_ERROR",
            message=exc.message,
            details={
                "url": exc.url,
                "timeout": exc.timeout,
                **exc.details
            }
        ).model_dump()
    )

# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint"""
    services = {}
    
    # Check Supabase connection
    try:
        if supabase_client:
            # Simple query to test connection
            supabase_client.client.table("listings").select("id").limit(1).execute()
            services["database"] = "healthy"
        else:
            services["database"] = "unavailable"
    except Exception as e:
        services["database"] = f"unhealthy: {str(e)}"
    
    # Check scraper
    services["scraper"] = "healthy" if scraper_instance else "unavailable"
    
    # Determine overall status
    overall_status = "healthy" if all(
        status == "healthy" for status in services.values()
    ) else "unhealthy"
    
    return HealthCheckResponse(
        status=overall_status,
        services=services
    )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "DublinMap API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# Scraping endpoints
@app.post("/scrape", response_model=ScrapingResponse)
async def scrape_properties(
    request: ScrapingRequest,
    background_tasks: BackgroundTasks,
    scraper: DaftScraper = Depends(get_scraper)
):
    """Scrape properties from Daft.ie"""
    start_time = time.time()
    
    try:
        logger.info(f"Starting scraping request: {request.model_dump()}")
        
        # Validate configuration
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise ConfigurationException(
                "Supabase configuration is missing",
                config_key="SUPABASE_URL/SUPABASE_KEY"
            )
        
        # Perform scraping based on type and limits
        if request.max_properties:
            # Use limited scraping when max_properties is specified
            if request.listing_type == "both":
                # For both types, we need to split the max_properties
                max_per_type = request.max_properties // 2
                results = {}
                
                # Scrape rent properties
                rent_result = scraper.scrape_limited_and_upload('rent', request.location, max_per_type)
                results['rent'] = rent_result
                
                # Scrape sale properties  
                sale_result = scraper.scrape_limited_and_upload('sale', request.location, max_per_type)
                results['sale'] = sale_result
                
                total_count = rent_result.get('count', 0) + sale_result.get('count', 0)
                result = {
                    "success": True,
                    "message": f"Scraped {total_count} total properties",
                    "count": total_count,
                    "details": results
                }
            else:
                result = scraper.scrape_limited_and_upload(
                    request.listing_type, 
                    request.location,
                    request.max_properties
                )
        else:
            # Use unlimited scraping when no max_properties specified
            if request.listing_type == "both":
                result = scraper.scrape_both_rent_and_sale(request.location)
            else:
                result = scraper.scrape_and_upload(
                    request.listing_type, 
                    request.location
                )
        
        execution_time = time.time() - start_time
        
        return ScrapingResponse(
            success=result["success"],
            message=result["message"],
            count=result.get("count", 0),
            details=result.get("details"),
            execution_time=execution_time
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Scraping failed: {str(e)}")
        
        if isinstance(e, DublinMapException):
            raise e
        
        raise ScrapingException(
            f"Scraping operation failed: {str(e)}",
            details={"execution_time": execution_time}
        )

@app.post("/scrape/async", response_model=ScrapingResponse)
async def scrape_properties_async(
    request: ScrapingRequest,
    background_tasks: BackgroundTasks,
    scraper: DaftScraper = Depends(get_scraper)
):
    """Start scraping operation in background"""
    try:
        logger.info(f"Starting async scraping request: {request.model_dump()}")
        
        # Add background task
        background_tasks.add_task(
            perform_scraping_task,
            request,
            scraper
        )
        
        return ScrapingResponse(
            success=True,
            message="Scraping operation started in background",
            count=0
        )
        
    except Exception as e:
        logger.error(f"Failed to start async scraping: {str(e)}")
        raise ScrapingException(f"Failed to start scraping operation: {str(e)}")

async def perform_scraping_task(request: ScrapingRequest, scraper: DaftScraper):
    """Background task for scraping"""
    try:
        logger.info(f"Executing background scraping task: {request.model_dump()}")
        
        # Perform scraping based on type and limits
        if request.max_properties:
            # Use limited scraping when max_properties is specified
            if request.listing_type == "both":
                # For both types, we need to split the max_properties
                max_per_type = request.max_properties // 2
                results = {}
                
                # Scrape rent properties
                rent_result = scraper.scrape_limited_and_upload('rent', request.location, max_per_type)
                results['rent'] = rent_result
                
                # Scrape sale properties  
                sale_result = scraper.scrape_limited_and_upload('sale', request.location, max_per_type)
                results['sale'] = sale_result
                
                total_count = rent_result.get('count', 0) + sale_result.get('count', 0)
                result = {
                    "success": True,
                    "message": f"Scraped {total_count} total properties",
                    "count": total_count,
                    "details": results
                }
            else:
                result = scraper.scrape_limited_and_upload(
                    request.listing_type, 
                    request.location,
                    request.max_properties
                )
        else:
            # Use unlimited scraping when no max_properties specified
            if request.listing_type == "both":
                result = scraper.scrape_both_rent_and_sale(request.location)
            else:
                result = scraper.scrape_and_upload(
                    request.listing_type, 
                    request.location
                )
        
        logger.info(f"Background scraping completed: {result}")
        
    except Exception as e:
        logger.error(f"Background scraping failed: {str(e)}")

# Property query endpoints
@app.get("/properties", response_model=PropertyListResponse)
async def get_properties(
    listing_type: Optional[str] = Query(None, description="Filter by listing type"),
    location: Optional[str] = Query(None, description="Filter by location"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    min_bedrooms: Optional[int] = Query(None, ge=0, le=10, description="Minimum bedrooms"),
    max_bedrooms: Optional[int] = Query(None, ge=0, le=10, description="Maximum bedrooms"),
    min_bathrooms: Optional[int] = Query(None, ge=0, le=10, description="Minimum bathrooms"),
    property_type: Optional[str] = Query(None, description="Property type"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Number to skip"),
    sort_by: str = Query("date_listed", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order"),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    """Get properties with filtering and pagination"""
    try:
        # Build query
        query = supabase.client.table("listings").select("*", count="exact")
        
        # Apply filters
        if listing_type:
            query = query.eq("listing_type", listing_type)
        if location:
            query = query.ilike("address_full", f"%{location}%")
        if min_price is not None:
            query = query.gte("price_eur", min_price)
        if max_price is not None:
            query = query.lte("price_eur", max_price)
        if min_bedrooms is not None:
            query = query.gte("bedrooms", min_bedrooms)
        if max_bedrooms is not None:
            query = query.lte("bedrooms", max_bedrooms)
        if min_bathrooms is not None:
            query = query.gte("bathrooms", min_bathrooms)
        if property_type:
            query = query.ilike("property_type", f"%{property_type}%")
        
        # Apply sorting
        if sort_order == "desc":
            query = query.order(sort_by, desc=True)
        else:
            query = query.order(sort_by, desc=False)
        
        # Apply pagination
        query = query.range(offset, offset + limit - 1)
        
        # Execute query
        result = query.execute()
        
        # Convert to response models
        properties = [PropertyResponse(**prop) for prop in result.data]
        
        return PropertyListResponse(
            properties=properties,
            total_count=result.count or 0,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < (result.count or 0)
        )
        
    except Exception as e:
        logger.error(f"Failed to query properties: {str(e)}")
        raise DatabaseException(f"Failed to query properties: {str(e)}", operation="select")

@app.get("/properties/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: int = Path(..., description="Property ID"),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    """Get a specific property by ID"""
    try:
        result = supabase.client.table("listings").select("*").eq("id", property_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Property not found")
        
        return PropertyResponse(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get property {property_id}: {str(e)}")
        raise DatabaseException(f"Failed to get property: {str(e)}", operation="select")

# Statistics endpoint
@app.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    """Get property statistics"""
    try:
        # Get total counts
        total_result = supabase.client.table("listings").select("id", count="exact").execute()
        total_count = total_result.count or 0
        
        # Get rent/sale counts
        rent_result = supabase.client.table("listings").select("id", count="exact").eq("listing_type", "rent").execute()
        rent_count = rent_result.count or 0
        
        sale_result = supabase.client.table("listings").select("id", count="exact").eq("listing_type", "sale").execute()
        sale_count = sale_result.count or 0
        
        # Get properties by location
        location_result = supabase.client.table("listings").select("address_full").execute()
        location_counts = {}
        for prop in location_result.data:
            if prop.get("address_full"):
                # Extract city from address (simple approach)
                address = prop["address_full"].lower()
                if "dublin" in address:
                    location_counts["dublin"] = location_counts.get("dublin", 0) + 1
                elif "cork" in address:
                    location_counts["cork"] = location_counts.get("cork", 0) + 1
                elif "galway" in address:
                    location_counts["galway"] = location_counts.get("galway", 0) + 1
                elif "limerick" in address:
                    location_counts["limerick"] = location_counts.get("limerick", 0) + 1
                elif "waterford" in address:
                    location_counts["waterford"] = location_counts.get("waterford", 0) + 1
        
        # Get properties by type
        type_result = supabase.client.table("listings").select("property_type").execute()
        type_counts = {}
        for prop in type_result.data:
            if prop.get("property_type"):
                prop_type = prop["property_type"]
                type_counts[prop_type] = type_counts.get(prop_type, 0) + 1
        
        # Get average prices
        rent_prices = supabase.client.table("listings").select("price_eur").eq("listing_type", "rent").not_.is_("price_eur", "null").execute()
        sale_prices = supabase.client.table("listings").select("price_eur").eq("listing_type", "sale").not_.is_("price_eur", "null").execute()
        
        avg_rent = None
        if rent_prices.data:
            prices = [p["price_eur"] for p in rent_prices.data if p["price_eur"]]
            avg_rent = sum(prices) / len(prices) if prices else None
        
        avg_sale = None
        if sale_prices.data:
            prices = [p["price_eur"] for p in sale_prices.data if p["price_eur"]]
            avg_sale = sum(prices) / len(prices) if prices else None
        
        # Get last updated
        last_updated_result = supabase.client.table("listings").select("inserted_at").order("inserted_at", desc=True).limit(1).execute()
        last_updated = None
        if last_updated_result.data:
            last_updated = last_updated_result.data[0]["inserted_at"]
        
        return StatisticsResponse(
            total_properties=total_count,
            rent_properties=rent_count,
            sale_properties=sale_count,
            properties_by_location=location_counts,
            properties_by_type=type_counts,
            average_price_rent=avg_rent,
            average_price_sale=avg_sale,
            last_updated=last_updated
        )
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {str(e)}")
        raise DatabaseException(f"Failed to get statistics: {str(e)}", operation="select")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
