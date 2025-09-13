import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseKey)

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
  inserted_at: string
}
