import requests
import json
import os
import csv
from datetime import datetime
from urllib.parse import urlparse

from datetime import datetime, date

def get_news_by_keywords(api_key, keywords, num_results=10, start_date_str=None, end_date_str=None):
    """
    Fetch news from Google News using SerpAPI for a user-specified date range based on user keywords
    Returns (raw_news_results, filtered_results)
    """
    # If no dates provided, use default: past 6 months
    today_dt = datetime.now()

    # Helper to parse various input formats
    def try_parse_input_date(d_str, default_min=True):
        if not d_str:
            return None
        # remove any whitespace
        d_str = d_str.strip()
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y%m%d", "%Y/%m/%d"]:
            try:
                dt = datetime.strptime(d_str, fmt)
                return datetime.combine(dt.date(), datetime.min.time()) if default_min else datetime.combine(dt.date(), datetime.max.time())
            except ValueError:
                continue
        raise ValueError(f"Could not parse date: {d_str}")

    # Determine start and end date objects
    if not start_date_str or not end_date_str:
        if today_dt.month == 1:
            start_month = 12
            start_year = today_dt.year - 1
        else:
            start_month = today_dt.month - 6
            start_year = today_dt.year
        s_date_obj = datetime(start_year, start_month, 1)
        e_date_obj = today_dt
    else:
        # PArse start date
        if isinstance(start_date_str, (date, datetime)):
             s_date_obj = datetime.combine(start_date_str, datetime.min.time()) if isinstance(start_date_str, date) and not isinstance(start_date_str, datetime) else start_date_str
        else:
             s_date_obj = try_parse_input_date(start_date_str, default_min=True)
        
        # Parse end date
        if isinstance(end_date_str, (date, datetime)):
             e_date_obj = datetime.combine(end_date_str, datetime.max.time()) if isinstance(end_date_str, date) and not isinstance(end_date_str, datetime) else end_date_str
        else:
             e_date_obj = try_parse_input_date(end_date_str, default_min=False)

    # Convert to MM/DD/YYYY string for Google Search API
    start_date_query = s_date_obj.strftime("%m/%d/%Y")
    end_date_query = e_date_obj.strftime("%m/%d/%Y")

    print(f"Searching for news from {start_date_query} to {end_date_query}")
    
    # SerpAPI endpoint for Google News
    url = "https://serpapi.com/search"
    
    # Parameters for the API request
    params = {
        "engine": "google",
        "tbm": "nws",
        "q": keywords,
        "api_key": api_key,
        "num": num_results,
        "hl": "en",
        "gl": "us",
        "tbs": f"cdr:1,cd_min:{start_date_query},cd_max:{end_date_query}"
    }
    
    try:
        # Make the API request
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Parse the JSON response
        data = response.json()
        
        # Extract news results
        news_results = []
        
        if "news_results" in data:
            for article in data["news_results"]:
                # Extract source name
                # In 'google' engine, source is often just a string name
                source_raw = article.get("source", "Unknown source")
                if isinstance(source_raw, dict):
                    source_name = source_raw.get("name", "Unknown source")
                    # source_url might vary, usually not provided in simple dict
                    source_url = "" 
                else:
                    source_name = str(source_raw)
                    source_url = ""
                
                # 'google' engine often doesn't give specific author list in main snippet
                # We'll just default to unknown or try to parse if hidden elsewhere
                author_name = "Unknown author"
                
                # Prefer 'published_at' (UTC iso) over 'date' (relative string)
                # 'date' might be "2 days ago" or "Nov 3, 2023"
                # 'published_at' is "2023-11-03 07:00:00 UTC"
                raw_date = article.get("published_at")
                if not raw_date:
                    raw_date = article.get("date", "No date available")

                news_item = {
                    "title": article.get("title", "No title available"),
                    "url": article.get("link", "No URL available"),
                    "source": source_name,
                    "author": author_name,
                    "timestamp": raw_date,
                    "source_url": source_url
                }
                news_results.append(news_item)
        
        # Filter articles by date range after fetching
        filtered_results = []
        # (Using s_date_obj / e_date_obj calculated at start)

        for article in news_results:
            article_date = parse_date_for_filtering(article['timestamp'])
            if s_date_obj <= article_date <= e_date_obj:
                filtered_results.append(article)
            else:
                print(f"Filtered out: {article['title']} - {article['timestamp']} (outside date range)")
        
        print(f"Found {len(news_results)} total articles, {len(filtered_results)} within date range")
        return news_results, filtered_results
        
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        return [], []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return [], []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return [], []

def sort_articles_by_source_and_date(news_list):
    """
    Sort articles by source first, then by recency (newest first)
    """
    # Sort by source first, then by date (newest first)
    return sorted(news_list, key=lambda x: (x['source'], -parse_date_for_filtering(x['timestamp']).timestamp()))

def parse_date_for_filtering(date_str):
    """
    Parse date string for filtering purposes
    Returns datetime object or datetime.min if unparseable
    Handles:
    - "MM/DD/YYYY, ..."
    - "X days ago"
    - "X hours ago"
    - "X minutes ago"
    - "Yesterday"
    """
    if not date_str:
        return datetime.min

    try:
        now = datetime.now()
        date_str = date_str.strip()

        # Handle "ago" relative dates
        if "ago" in date_str.lower():
            if "minute" in date_str.lower():
                minutes = int(date_str.split()[0])
                from datetime import timedelta
                return now - timedelta(minutes=minutes)
            elif "hour" in date_str.lower():
                hours = int(date_str.split()[0])
                from datetime import timedelta
                return now - timedelta(hours=hours)
            elif "day" in date_str.lower():
                days = int(date_str.split()[0])
                from datetime import timedelta
                return now - timedelta(days=days)
            elif "week" in date_str.lower():
                weeks = int(date_str.split()[0])
                from datetime import timedelta
                return now - timedelta(weeks=weeks)
            elif "month" in date_str.lower():
                months = int(date_str.split()[0])
                from datetime import timedelta
                # Approx
                return now - timedelta(days=months*30)
            elif "year" in date_str.lower():
                years = int(date_str.split()[0])
                from datetime import timedelta
                return now - timedelta(days=years*365)
        
        # Handle "Yesterday"
        if "yesterday" in date_str.lower():
            from datetime import timedelta
            return now - timedelta(days=1)

        # Handle explicit formats
        # "07/02/2025, 05:49 PM, +0000 UTC"
        if "," in date_str and "UTC" in date_str:
            date_part = date_str.split(",")[0].strip()  # Get "07/02/2025"
            try:
                return datetime.strptime(date_part, "%m/%d/%Y")
            except ValueError:
                pass
        
        # Handle ISO-like format "2023-03-26 07:00:00 UTC"
        if "UTC" in date_str and "-" in date_str:
             # trim " UTC" and parse
             clean_str = date_str.replace(" UTC", "").strip()
             try:
                 return datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
             except ValueError:
                 pass

        # Try simple formats
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%b %d, %Y", "%d %b %Y"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return datetime.min
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        return datetime.min

def ensure_result_folder(folder="result"):
    if not os.path.exists(folder):
        os.makedirs(folder)
    return folder

def save_news_to_txt(news_list, keywords, timestamp=None, folder="result", suffix=""):
    ensure_result_folder(folder)
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_keywords = keywords.replace(' ', '_')
    filename = f"{timestamp}_{safe_keywords}{suffix}.txt"
    filepath = os.path.join(folder, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(f"NEWS SEARCH RESULTS - KEYWORDS: {keywords.upper()}\n")
            file.write("=" * 50 + "\n\n")
            file.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for i, article in enumerate(news_list, 1):
                file.write(f"Article {i}:\n")
                file.write(f"Title: {article['title']}\n")
                file.write(f"URL: {article['url']}\n")
                file.write(f"Source: {article['source']}\n")
                file.write(f"Author: {article['author']}\n")
                file.write(f"Timestamp: {article['timestamp']}\n")
                file.write("-" * 40 + "\n\n")
        print(f"Successfully saved {len(news_list)} articles to {filepath}")
        return filepath
    except Exception as e:
        print(f"Error saving to txt file: {e}")
        return None

def save_initial_articles_to_csv(news_list, keywords, timestamp=None, folder="result", suffix=""):
    ensure_result_folder(folder)
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_keywords = keywords.replace(' ', '_')
    filename = f"{timestamp}_{safe_keywords}{suffix}.csv"
    filepath = os.path.join(folder, filename)
    try:
        with open(filepath, 'w', encoding='utf-8', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["number", "source", "source_url", "date", "author", "title", "url"])
            for i, article in enumerate(news_list, 1):
                writer.writerow([
                    i,
                    article.get('source', ''),
                    article.get('source_url', ''),
                    article.get('timestamp', ''),
                    article.get('author', ''),
                    article.get('title', ''),
                    article.get('url', '')
                ])
        print(f"Saved articles to {filepath}")
        return filepath
    except Exception as e:
        print(f"Error saving articles to CSV: {e}")
        return None

def read_media_list(filename="media.txt"):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return set(line.strip().lower() for line in f if line.strip())
    except FileNotFoundError:
        print(f"Media list file '{filename}' not found. No filtering will be applied.")
        return set()
    except Exception as e:
        print(f"Error reading media list: {e}")
        return set()

def extract_domain(url):
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""

def filter_articles_by_media(news_list, allowed_media_set):
    if not allowed_media_set:
        return news_list
    allowed_domains = set()
    for entry in allowed_media_set:
        entry = entry.strip().lower().rstrip('/')
        domain = extract_domain(entry)
        if domain:
            allowed_domains.add(domain)
        else:
            allowed_domains.add(entry)
    filtered = []
    for article in news_list:
        source_url = (article.get('source_url') or '').strip().lower()
        article_url = (article.get('url') or '').strip().lower()
        source_domain = extract_domain(source_url)
        article_domain = extract_domain(article_url)
        matched = False
        for allowed_domain in allowed_domains:
            if allowed_domain and (
                allowed_domain in source_domain or allowed_domain in article_domain
            ):
                matched = True
                break
        if matched:
            filtered.append(article)
    print(f"Filtered to {len(filtered)} articles from allowed media domains.")
    return filtered
