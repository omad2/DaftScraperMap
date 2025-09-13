class DublinMapException(Exception):
    """Base exception for DublinMap application"""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class ScrapingException(DublinMapException):
    """Exception raised during scraping operations"""
    def __init__(self, message: str, url: str = None, status_code: int = None, details: dict = None):
        self.url = url
        self.status_code = status_code
        super().__init__(message, "SCRAPING_ERROR", details)

class ValidationException(DublinMapException):
    """Exception raised during data validation"""
    def __init__(self, message: str, field: str = None, value: str = None, details: dict = None):
        self.field = field
        self.value = value
        super().__init__(message, "VALIDATION_ERROR", details)

class DatabaseException(DublinMapException):
    """Exception raised during database operations"""
    def __init__(self, message: str, operation: str = None, table: str = None, details: dict = None):
        self.operation = operation
        self.table = table
        super().__init__(message, "DATABASE_ERROR", details)

class ConfigurationException(DublinMapException):
    """Exception raised for configuration issues"""
    def __init__(self, message: str, config_key: str = None, details: dict = None):
        self.config_key = config_key
        super().__init__(message, "CONFIG_ERROR", details)

class RateLimitException(DublinMapException):
    """Exception raised when rate limits are exceeded"""
    def __init__(self, message: str, retry_after: int = None, details: dict = None):
        self.retry_after = retry_after
        super().__init__(message, "RATE_LIMIT_ERROR", details)

class NetworkException(DublinMapException):
    """Exception raised for network-related errors"""
    def __init__(self, message: str, url: str = None, timeout: bool = False, details: dict = None):
        self.url = url
        self.timeout = timeout
        super().__init__(message, "NETWORK_ERROR", details)
