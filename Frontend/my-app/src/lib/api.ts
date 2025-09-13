/**
 * API client for DublinMap FastAPI backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface Property {
  id: number
  url: string
  title: string
  listing_type: 'rent' | 'sale'
  price_eur: number | null
  price_period: string | null
  bedrooms: number | null
  bathrooms: number | null
  property_type: string | null
  size_sqm: number | null
  latitude: number | null
  longitude: number | null
  date_listed: string | null
  image_url: string | null
  address_full: string | null
  inserted_at: string
}

export interface PropertyListResponse {
  properties: Property[]
  total_count: number
  limit: number
  offset: number
  has_more: boolean
}


export interface StatisticsResponse {
  total_properties: number
  rent_properties: number
  sale_properties: number
  properties_by_location: Record<string, number>
  properties_by_type: Record<string, number>
  average_price_rent: number | null
  average_price_sale: number | null
  last_updated: string | null
}

export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy'
  timestamp: string
  version: string
  services: Record<string, string>
}

export interface PropertyFilters {
  listing_type?: 'rent' | 'sale'
  location?: string
  min_price?: number
  max_price?: number
  min_bedrooms?: number
  max_bedrooms?: number
  min_bathrooms?: number
  property_type?: string
  limit?: number
  offset?: number
  sort_by?: 'price_eur' | 'date_listed' | 'bedrooms' | 'bathrooms'
  sort_order?: 'asc' | 'desc'
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }

    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(
          errorData.message || `HTTP ${response.status}: ${response.statusText}`
        )
      }

      return await response.json()
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error)
      throw error
    }
  }

  // Health check
  async getHealth(): Promise<HealthCheckResponse> {
    return this.request<HealthCheckResponse>('/health')
  }

  // Properties
  async getProperties(filters: PropertyFilters = {}): Promise<PropertyListResponse> {
    const params = new URLSearchParams()
    
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, value.toString())
      }
    })

    const queryString = params.toString()
    const endpoint = queryString ? `/properties?${queryString}` : '/properties'
    
    return this.request<PropertyListResponse>(endpoint)
  }

  async getProperty(id: number): Promise<Property> {
    return this.request<Property>(`/properties/${id}`)
  }

  // Statistics
  async getStatistics(): Promise<StatisticsResponse> {
    return this.request<StatisticsResponse>('/statistics')
  }


  // Utility methods
  async isHealthy(): Promise<boolean> {
    try {
      const health = await this.getHealth()
      return health.status === 'healthy'
    } catch {
      return false
    }
  }
}

// Export singleton instance
export const apiClient = new ApiClient()

// Export class for testing
export { ApiClient }
