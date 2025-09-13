'use client'

import { useState } from 'react'
import PropertyGrid from '@/components/PropertyGrid'
import PropertyFilters from '@/components/PropertyFilters'
import { PropertyFilters as PropertyFiltersType } from '@/lib/api'

export default function Home() {
  const [filters, setFilters] = useState<PropertyFiltersType>({
    limit: 20,
    offset: 0,
    sort_by: 'date_listed',
    sort_order: 'desc'
  })

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">DublinMap</h1>
          <p className="text-gray-600">Property management platform</p>
        </div>

        {/* Main Content */}
        <div className="space-y-6">
          <PropertyFilters filters={filters} onFiltersChange={setFilters} />
          <PropertyGrid filters={filters} />
        </div>
      </div>
    </div>
  )
}
