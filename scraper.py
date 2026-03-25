import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
from database import item_already_found, add_found_item

def search_ebay(query, max_price):
    """Search eBay for items matching query under max_price"""
    # Format: query with max price filter
    # eBay URL format: _sacat=0 for all categories, price_max for max price
    encoded_query = urllib.parse.quote(query)
    
    # Construct eBay search URL with price filter
    url = f"https://www.ebay.com/sch/i.html?_nkw={encoded_query}&_udhi={max_price}&_sacat=0&LH_BIN=1&rt=nc"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        items = []
        
        # eBay item containers
        # Look for the item list
        item_containers = soup.find_all('div', {'class': 's-item__wrapper clearfix'})
        
        for container in item_containers[:10]:  # Limit to first 10 items
            try:
                # Title
                title_elem = container.find('div', {'class': 's-item__title'})
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                
                # Skip placeholder items
                if title == 'Shop on eBay':
                    continue
                
                # Price
                price_elem = container.find('span', {'class': 's-item__price'})
                price = price_elem.get_text(strip=True) if price_elem else 'Price not shown'
                
                # URL
                link_elem = container.find('a', {'class': 's-item__link'})
                if not link_elem:
                    continue
                item_url = link_elem.get('href', '')
                
                items.append({
                    'title': title,
                    'price': price,
                    'url': item_url
                })
            except Exception as e:
                continue
        
        return items
        
    except Exception as e:
        print(f"Error searching eBay: {e}")
        return []

def check_all_searches():
    """Check all active searches and return new findings"""
    from database import get_active_searches, update_last_check
    
    searches = get_active_searches()
    new_findings = []
    
    for search in searches:
        search_id, title, max_price, email, created_at, last_check, active = search
        
        print(f"Checking: {title} (max ${max_price})")
        
        items = search_ebay(title, max_price)
        
        for item in items:
            if not item_already_found(search_id, item['url']):
                add_found_item(search_id, item['title'], item['price'], item['url'], 'eBay')
                new_findings.append({
                    'search_title': title,
                    'item_title': item['title'],
                    'price': item['price'],
                    'url': item['url'],
                    'email': email
                })
        
        update_last_check(search_id)
    
    return new_findings