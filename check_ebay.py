#!/usr/bin/env python3
"""
Rare Parts Hunter - eBay Finding API
Uses official eBay Finding API (free)
"""
import os
import json
import sys
import re
import requests
from urllib.parse import quote_plus

print("=== RARE PARTS HUNTER STARTING ===", flush=True)

CONFIG_PATH = 'config.json'
SEEN_PATH = 'seen.json'

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def load_seen():
    if not os.path.exists(SEEN_PATH):
        return set()
    with open(SEEN_PATH, 'r') as f:
        try:
            return set(json.load(f))
        except:
            return set()

def save_seen(seen):
    with open(SEEN_PATH, 'w') as f:
        json.dump(list(seen), f)

def scrape_ebay_api(query, max_price):
    """Use eBay Finding API"""
    
    # eBay Finding API endpoint
    endpoint = "https://svcs.ebay.com/services/search/FindingService/v1"
    
    app_id = os.getenv('EBAY_APP_ID')
    if not app_id:
        print("ERROR: EBAY_APP_ID not set in secrets!", flush=True)
        print("Get free API key at: https://developer.ebay.com/api-keys", flush=True)
        return []
    
    params = {
        'OPERATION-NAME': 'findItemsByKeywords',
        'SERVICE-VERSION': '1.13.0',
        'SECURITY-APPNAME': app_id,
        'RESPONSE-DATA-FORMAT': 'JSON',
        'keywords': query,
        'itemFilter(0).name': 'MaxPrice',
        'itemFilter(0).value': str(max_price),
        'itemFilter(0).paramName': 'Currency',
        'itemFilter(0).paramValue': 'USD',
        'paginationInput.entriesPerPage': '50',
    }
    
    print(f"Calling eBay Finding API for: {query}", flush=True)
    
    try:
        resp = requests.get(endpoint, params=params, timeout=30)
        print(f"Response status: {resp.status_code}", flush=True)
        
        if resp.status_code != 200:
            print(f"Error: {resp.text[:500]}", flush=True)
            return []
        
        data = resp.json()
        
        # Check for errors
        if 'findItemsByKeywordsResponse' in data:
            response = data['findItemsByKeywordsResponse']
            
            if 'ack' in response:
                ack = response['ack']
                print(f"API ack: {ack}", flush=True)
            
            if 'searchResult' in response:
                search_result = response['searchResult']
                
                if 'item' in search_result:
                    items = search_result['item']
                    print(f"Found {len(items)} items via API", flush=True)
                    
                    results = []
                    for item in items:
                        try:
                            item_id = item.get('itemId', '')
                            title = item.get('title', '')
                            price = float(item.get('sellingStatus', [{}])[0].get('currentPrice', [{}])[0].get('value', '999999'))
                            link = item.get('viewItemURL', '')
                            
                            results.append({
                                'id': item_id,
                                'title': title,
                                'price': price,
                                'link': link
                            })
                        except Exception as e:
                            print(f"Error parsing item: {e}", flush=True)
                    
                    return results
        
        print(f"Response: {str(data)[:500]}", flush=True)
        return []
        
    except Exception as e:
        print(f"Exception: {e}", flush=True)
        return []

def send_email_sendgrid(to_email, subject, html_content):
    api_key = os.getenv('SENDGRID_API_KEY')
    print(f"SENDGRID_API_KEY present: {bool(api_key)}", flush=True)
    if not api_key:
        print("ERROR: SENDGRID_API_KEY not set!", flush=True)
        return
    
    url = 'https://api.sendgrid.com/v3/mail/send'
    payload = {
        'personalizations': [{'to': [{'email': to_email}], 'subject': subject}],
        'from': {'email': 'no-reply@rareparts.example'},
        'content': [{'type': 'text/html', 'value': html_content}]
    }
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    r = requests.post(url, headers=headers, json=payload)
    print(f"SendGrid response: {r.status_code}", flush=True)

def notify_matches(matches, config):
    if not matches:
        print("No matches to notify", flush=True)
        return
    to_email = config['email']
    subject = f"Rare Parts Hunter: {len(matches)} new match(es)"
    html_lines = [f"<h2>{subject}</h2>", '<ul>']
    for m in matches:
        html_lines.append(f"<li><a href=\"{m['link']}\">{m['title']}</a> — ${m['price']}</li>")
    html_lines.append('</ul>')
    html_content = '\n'.join(html_lines)
    method = os.getenv('EMAIL_METHOD', 'sendgrid').lower()
    if method == 'sendgrid':
        send_email_sendgrid(to_email, subject, html_content)

def main():
    config = load_config()
    query = config['query']
    max_price = float(config.get('max_price', 9999999))
    seen = load_seen()
    print(f"Searching for: {query} (max ${max_price})", flush=True)
    
    items = scrape_ebay_api(query, max_price)
    print(f"=== FOUND {len(items)} ITEMS ===", flush=True)
    
    new_matches = []
    for it in items:
        if not it['id']:
            continue
        if it['id'] in seen:
            continue
        if it['price'] <= max_price:
            print(f"NEW MATCH: {it['title'][:50]} — ${it['price']}", flush=True)
            new_matches.append(it)
            seen.add(it['id'])
    
    print(f"=== {len(new_matches)} NEW MATCHES ===", flush=True)
    
    if new_matches:
        notify_matches(new_matches, config)
    
    save_seen(seen)
    print("=== DONE ===", flush=True)

if __name__ == '__main__':
    main()
