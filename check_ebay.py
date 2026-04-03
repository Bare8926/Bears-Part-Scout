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
from urllib.parse import quote_plus, urlencode

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

def scrape_listings(query):
    # Try different eBay endpoints
    endpoints = [
        # Regular search
        f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(query)}&_sop=10",
        # Using different URL format
        f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(query)}&LH_BIN=1&_sop=10",
        # Try the new v3 API
        f"https://www.ebay.com/buy/browseapi/v1/find?keywords={quote_plus(query)}&limit=48",
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/html, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.ebay.com/',
    })
    
    for url in endpoints[:1]:  # Try first one
        print(f"Trying: {url[:80]}...", flush=True)
        
        try:
            resp = session.get(url, timeout=30)
            print(f"Status: {resp.status_code}, Content-Type: {resp.headers.get('Content-Type', 'unknown')}", flush=True)
            
            # Check if it's JSON
            if 'application/json' in resp.headers.get('Content-Type', ''):
                print("Response is JSON!", flush=True)
                try:
                    data = resp.json()
                    print(f"JSON keys: {list(data.keys()) if isinstance(data, dict) else 'list'}", flush=True)
                except:
                    pass
            
            # Check for inline JSON data in HTML
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Look for script tags with JSON data
            scripts = soup.find_all('script', type=re.compile('application/ld\+json|application/json'))
            print(f"Found {len(scripts)} JSON scripts", flush=True)
            
            # Look for data in __INITIAL_STATE__ or similar
            for script in scripts[:3]:
                if script.string:
                    print(f"Script preview: {script.string[:200]}...", flush=True)
            
            # Try finding items by looking at all text content
            text_content = soup.get_text()[:500]
            print(f"Page text preview: {text_content}", flush=True)
            
            return []
            
        except Exception as e:
            print(f"Error: {e}", flush=True)
    
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
    
    items = scrape_listings(query)
    
    new_matches = []
    for it in items:
        if it['id'] in seen:
            continue
        if it['price'] <= max_price:
            print(f"NEW MATCH: {it['title']} — ${it['price']}", flush=True)
            new_matches.append(it)
            seen.add(it['id'])
    
    if new_matches:
        notify_matches(new_matches, config)
    
    save_seen(seen)
    print("=== DONE ===", flush=True)

if __name__ == '__main__':
    main()
