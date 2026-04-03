#!/usr/bin/env python3
"""
Rare Parts Hunter - eBay scraper
"""
import os
import json
import sys
import re
import time
import requests
from bs4 import BeautifulSoup
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

def fetch_with_retry(url, max_retries=3):
    """Fetch URL with retry logic"""
    
    headers_list = [
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        },
        {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    ]
    
    for attempt in range(max_retries):
        headers = headers_list[attempt % len(headers_list)]
        
        print(f"Attempt {attempt + 1}: Fetching {url}", flush=True)
        
        session = requests.Session()
        session.headers.update(headers)
        
        try:
            resp = session.get(url, timeout=30)
            print(f"Response status: {resp.status_code}", flush=True)
            
            if resp.status_code == 200:
                return resp
            elif resp.status_code == 503:
                # Wait before retry
                wait_time = (attempt + 1) * 5
                print(f"503 error, waiting {wait_time} seconds before retry...", flush=True)
                time.sleep(wait_time)
            else:
                return resp
                
        except Exception as e:
            print(f"Error: {e}", flush=True)
            time.sleep(3)
    
    return None

def scrape_listings(query):
    url = f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(query)}&_sop=10"
    
    resp = fetch_with_retry(url)
    if not resp:
        print("Failed to fetch after retries", flush=True)
        return []
    
    if resp.status_code != 200:
        print(f"ERROR: eBay returned {resp.status_code}", flush=True)
        return []
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Find all links that point to /itm/
    items = soup.find_all('a', href=re.compile(r'/itm/\d+'))
    
    print(f"Found {len(items)} item links", flush=True)
    
    results = []
    seen_ids = set()
    
    for link in items:
        href = link.get('href', '')
        
        # Extract item ID
        id_match = re.search(r'/itm/(\d+)', href)
        if not id_match:
            continue
        item_id = id_match.group(1)
        
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)
        
        # Get title
        title = link.get_text(strip=True)
        if not title:
            parent = link.parent
            if parent:
                title_elem = parent.select_one('.s-item__title, h3, .item-title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
        
        if not title or title == 'Shop on eBay':
            continue
        
        # Get price
        price = 9999999.0
        parent = link.parent
        if parent:
            price_elem = parent.select_one('.s-item__price, .price')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                if price_match:
                    try:
                        price = float(price_match.group())
                    except:
                        pass
        
        results.append({
            'id': item_id,
            'title': title[:100],
            'price': price,
            'link': href
        })
    
    return results

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
    if r.status_code >= 400:
        print(f"SendGrid error: {r.text}", flush=True)
    else:
        print("Email sent successfully!", flush=True)

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
    print(f"Sending email via {method}", flush=True)
    if method == 'sendgrid':
        send_email_sendgrid(to_email, subject, html_content)

def main():
    config = load_config()
    query = config['query']
    max_price = float(config.get('max_price', 9999999))
    seen = load_seen()
    print(f"Searching for: {query} (max ${max_price})", flush=True)
    
    items = scrape_listings(query)
    print(f"=== FOUND {len(items)} PARSED ITEMS ===", flush=True)
    
    new_matches = []
    for it in items:
        if not it['id']:
            continue
        if it['id'] in seen:
            continue
        if it['price'] <= max_price:
            print(f"NEW MATCH: {it['title']} — ${it['price']}", flush=True)
            new_matches.append(it)
            seen.add(it['id'])
        else:
            print(f"Too expensive: {it['title'][:50]} — ${it['price']}", flush=True)
    
    print(f"=== {len(new_matches)} NEW MATCHES ===", flush=True)
    
    if new_matches:
        notify_matches(new_matches, config)
    
    save_seen(seen)
    print("=== DONE ===", flush=True)

if __name__ == '__main__':
    main()
