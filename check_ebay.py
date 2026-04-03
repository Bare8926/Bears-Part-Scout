#!/usr/bin/env python3
"""
Rare Parts Hunter - eBay scraper
Checks eBay search results and emails new matches.
"""
import os
import json
import sys
import time
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

print("=== RARE PARTS HUNTER STARTING ===", flush=True)
print(f"Python version: {sys.version}", flush=True)

# Configuration
CONFIG_PATH = 'config.json'
SEEN_PATH = 'seen.json'

def load_config():
    print(f"Loading config from {CONFIG_PATH}...", flush=True)
    if not os.path.exists(CONFIG_PATH):
        print(f"ERROR: {CONFIG_PATH} not found!", flush=True)
        sys.exit(1)
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    print(f"Config: {config}", flush=True)
    return config

def load_seen():
    print(f"Loading seen items from {SEEN_PATH}...", flush=True)
    if not os.path.exists(SEEN_PATH):
        print("No seen.json found, starting fresh", flush=True)
        return set()
    with open(SEEN_PATH, 'r') as f:
        try:
            return set(json.load(f))
        except Exception:
            return set()

def save_seen(seen):
    with open(SEEN_PATH, 'w') as f:
        json.dump(list(seen), f)

def build_search_url(query):
    return f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(query)}&_sop=10"

def parse_price(price_str):
    if not price_str:
        return 9999999.0
    s = price_str.replace('$', '').replace(',', '').strip()
    parts = s.split(' ')
    try:
        return float(parts[0])
    except Exception:
        return 9999999.0

def scrape_listings(query):
    url = build_search_url(query)
    print(f"Fetching: {url}", flush=True)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    resp = requests.get(url, headers=headers, timeout=30)
    print(f"Response status: {resp.status_code}", flush=True)
    soup = BeautifulSoup(resp.text, 'html.parser')
    items = []
    for item in soup.select('.s-item'):
        title_tag = item.select_one('.s-item__title')
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        link_tag = item.select_one('.s-item__link')
        link = link_tag['href'] if link_tag and link_tag.has_attr('href') else None
        price_tag = item.select_one('.s-item__price')
        price = parse_price(price_tag.get_text(strip=True)) if price_tag else 9999999.0
        item_id = None
        if link:
            import re
            m = re.search(r'/itm/([0-9]+)', link)
            if m:
                item_id = m.group(1)
            else:
                item_id = link
        items.append({'id': item_id, 'title': title, 'price': price, 'link': link})
    return items

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
    else:
        print(f"Unknown email method: {method}", flush=True)

def main():
    config = load_config()
    query = config['query']
    max_price = float(config.get('max_price', 9999999))
    seen = load_seen()
    print(f"Searching for: {query} (max ${max_price})", flush=True)
    items = scrape_listings(query)
    print(f"=== FOUND {len(items)} ITEMS ===", flush=True)
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
    print(f"=== {len(new_matches)} NEW MATCHES ===", flush=True)
    if new_matches:
        notify_matches(new_matches, config)
    save_seen(seen)
    print("=== DONE ===", flush=True)

if __name__ == '__main__':
    main()
