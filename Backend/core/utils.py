import re
import time
from typing import Optional, Dict, Any
from loguru import logger
from models import ParsedPriceResult, ParsedBedsResult

DUBLIN_AREAS = [
    'artane', 'ballsbridge', 'ballymun', 'beaumont', 'blackrock', 'booterstown',
    'cabinteely', 'castleknock', 'chapelizod', 'clondalkin', 'clonsilla', 'clonskeagh',
    'clontarf', 'coolock', 'crumlin', 'dalkey', 'donabate', 'donaghmede', 'donnybrook',
    'drumcondra', 'dun-laoghaire', 'dundrum', 'fairview', 'finglas', 'firhouse',
    'foxrock', 'glasnevin', 'glenageary', 'harolds-cross', 'howth', 'irishtown',
    'kilmainham', 'kilternan', 'kimmage', 'leopardstown', 'liffey-valley', 'lucan',
    'malahide', 'marino', 'merrion', 'milltown', 'monkstown', 'mount-merrion',
    'mulhuddart', 'palmerstown', 'portmarnock', 'raheny', 'ranelagh', 'rathcoole',
    'rathfarnham', 'rathgar', 'rathmines', 'ringsend', 'rush', 'saggart',
    'sallynoggin', 'sandycove', 'sandyford', 'sandymount', 'shankill', 'skerries',
    'stepaside', 'stillorgan', 'sutton', 'swords', 'tallaght', 'templeogue',
    'terenure', 'walkinstown', 'whitehall'
]

def parse_price(price_string: Optional[str]) -> ParsedPriceResult:
    if not price_string or not isinstance(price_string, str):
        return ParsedPriceResult(value=None, type='unknown')

    price_str_normalized = price_string.lower()

    if 'price on application' in price_str_normalized or 'contact agent' in price_str_normalized:
        return ParsedPriceResult(value=None, type='on_application')

    match = re.search(
        r'(?:€\s*)?([\d,]+(?:\.\d{2})?)\s*(?:(?:per\s*)?(month|week|mth|wk|pm|p/m|pw|p/w|perweek))?',
        price_str_normalized
    )

    if match and match.group(1):
        try:
            amount = float(match.group(1).replace(',', ''))
            period_word = match.group(2).lower() if match.group(2) else None

            if period_word:
                if period_word.startswith('week') or period_word.startswith('wk') or period_word in ['pw', 'p/w', 'perweek']:
                    amount = round((amount * 52) / 12)
                return ParsedPriceResult(value=amount, type='numeric')
            elif '€' in price_str_normalized:
                return ParsedPriceResult(value=amount, type='numeric')
        except ValueError:
            pass

    simple_numeric = re.sub(r'[^0-9.]', '', price_string)
    if simple_numeric and simple_numeric == re.sub(r'[^0-9€\s.,]', '', price_string):
        try:
            potential_price = float(simple_numeric)
            if potential_price >= 100 and ('€' in price_str_normalized or 'per month' in price_str_normalized or 'per week' in price_str_normalized):
                return ParsedPriceResult(value=potential_price, type='numeric')
        except ValueError:
            pass

    return ParsedPriceResult(value=None, type='unknown')

def parse_beds(bed_string: Optional[str]) -> Optional[ParsedBedsResult]:
    if not bed_string or not isinstance(bed_string, str):
        return None

    bed_str_normalized = bed_string.lower()

    if 'studio' in bed_str_normalized:
        return ParsedBedsResult(min=1, max=1, is_studio=True)

    range_match = re.search(r'(\d+)\s*(?:to|-)\s*(\d+)\s*bed', bed_str_normalized)
    if range_match:
        try:
            min_beds = int(range_match.group(1))
            max_beds = int(range_match.group(2))
            return ParsedBedsResult(min=min(min_beds, max_beds), max=max(min_beds, max_beds))
        except ValueError:
            pass

    single_match = re.search(r'(\d+)\s*bed', bed_str_normalized)
    if single_match:
        try:
            num = int(single_match.group(1))
            return ParsedBedsResult(min=num, max=num)
        except ValueError:
            pass

    return None

def parse_bathrooms(bath_string: Optional[str]) -> Optional[int]:
    if not bath_string or not isinstance(bath_string, str):
        return None

    bath_str_normalized = bath_string.lower()
    match = re.search(r'(\d+)\s*bath', bath_str_normalized)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return None

def extract_lat_lng(html: str, selector: str = 'a[data-testid="satelite-button"]') -> Optional[Dict[str, float]]:
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html, 'html.parser')
    link = soup.select_one(selector)
    
    if link and link.get('href'):
        href = link.get('href')
        match = re.search(r'q=loc:([\d.-]+)\+([\d.-]+)', href) or re.search(r'viewpoint=([\d.-]+),([\d.-]+)', href)
        if match:
            try:
                lat = float(match.group(1))
                lng = float(match.group(2))
                return {'lat': lat, 'lng': lng}
            except ValueError:
                pass
    
    return None

def slugify(text: str) -> str:
    if not isinstance(text, str):
        return ''
    
    return re.sub(r'[^a-z0-9-]', '', text.lower().replace(' ', '-'))

def generate_daft_location_slug(location_string: str) -> str:
    if not isinstance(location_string, str) or not location_string.strip():
        return ''

    parts = [slugify(part.strip()) for part in location_string.split(',') if part.strip()]
    
    if len(parts) == 2:
        return '-'.join(parts)
    
    single_part_slug = slugify(location_string)
    
    if re.match(r'^dublin-\d+$', single_part_slug):
        return f'{single_part_slug}-dublin'
    
    if single_part_slug in DUBLIN_AREAS:
        return f'{single_part_slug}-dublin'
    
    return single_part_slug

def delay(ms: int):
    time.sleep(ms / 1000.0)

def format_ber(ber: Optional[str]) -> Optional[str]:
    if not ber:
        return None
    
    cleaned_ber = ber.replace('BER ', '').strip()
    if cleaned_ber == 'SI_666':
        return 'Exempt'
    return cleaned_ber
