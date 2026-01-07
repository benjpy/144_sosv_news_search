import os
import csv
import smtplib
import requests
import tldextract
from datetime import datetime, timedelta
from urllib.parse import urlparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from zoneinfo import ZoneInfo


# -------------------- Helpers --------------------

def read_file_lines(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return []

def read_api_key_from_file(filename):
    lines = read_file_lines(filename)
    return lines[0] if lines else None

def read_gmail_credentials(filename):
    lines = read_file_lines(filename)
    if len(lines) >= 2:
        return lines[0], lines[1]
    return None, None

def get_past_week_dates():
    today = datetime.now(ZoneInfo("America/New_York"))
    last_sunday = today - timedelta(days=today.weekday() + 1)
    last_monday = last_sunday - timedelta(days=6)
    return last_monday.strftime("%Y-%m-%d"), last_sunday.strftime("%Y-%m-%d")


# -------------------- Fetch & Filter --------------------

def get_news_by_keywords(api_key, keywords, num_results=100, start_date_str=None, end_date_str=None):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_news",
        "q": keywords,
        "api_key": api_key,
        "num": num_results,
        "hl": "en",
        "gl": "us",
        "tbs": f"cdr:1,cd_min:{start_date_str},cd_max:{end_date_str}"
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        news_results = []
        if "news_results" in data:
            for article in data["news_results"]:
                source = article.get("source", {})
                source_name = source.get("name", "Unknown source") if isinstance(source, dict) else str(source)
                source_url = source.get("link", "") if isinstance(source, dict) else ""
                author = source.get("authors", "Unknown author") if isinstance(source, dict) else "Unknown author"
                if isinstance(author, list):
                    author = ", ".join(author)
                news_results.append({
                    "title": article.get("title", "No title available"),
                    "url": article.get("link", "No URL available"),
                    "source": source_name,
                    "author": author,
                    "timestamp": article.get("date", "No date available"),
                    "source_url": source_url
                })
        return news_results
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []

def parse_article_date(date_str):
    try:
        if "," in date_str:
            return datetime.strptime(date_str.split(",")[0], "%m/%d/%Y")
    except:
        pass
    return None

def filter_articles_by_date(news_list, start_date_str, end_date_str):
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    return [
        article for article in news_list
        if (parsed := parse_article_date(article.get("timestamp"))) and start_date <= parsed <= end_date
    ]

def extract_registered_domain(url):
    try:
        extracted = tldextract.extract(url)
        if extracted.domain and extracted.suffix:
            return f"{extracted.domain}.{extracted.suffix}".lower()
    except:
        pass
    return ""

def filter_articles_by_media(news_list, allowed_media):
    allowed_domains = {extract_registered_domain(url) for url in allowed_media}
    filtered = []
    for article in news_list:
        url_domain = extract_registered_domain(article.get("url", ""))
        source_domain = extract_registered_domain(article.get("source_url", ""))
        if url_domain in allowed_domains or source_domain in allowed_domains:
            filtered.append(article)
    return filtered

def sort_articles_by_source_and_date(news_list):
    def parse_date(date_str):
        try:
            if date_str and "," in date_str:
                return datetime.strptime(date_str.split(",")[0], "%m/%d/%Y")
        except:
            return datetime.min
    return sorted(news_list, key=lambda x: (x['source'], -parse_date(x['timestamp']).timestamp()))


# -------------------- Save & Send --------------------

def save_news_to_csv(news_list, topic, filename, folder="result"):
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, 'w', encoding='utf-8', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["number", "source", "date", "author", "title", "url"])
        for i, article in enumerate(news_list, 1):
            writer.writerow([
                i,
                article['source'],
                article['timestamp'],
                article['author'],
                article['title'],
                article['url']
            ])
    return filepath

def save_news_to_txt(news_list, topic, timestamp, folder="result"):
    os.makedirs(folder, exist_ok=True)
    filename = f"{timestamp}_{topic.replace(' ', '_')}.txt"
    filepath = os.path.join(folder, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"NEWS SEARCH RESULTS - KEYWORDS: {topic.upper()}\n")
        f.write("=" * 50 + "\n\n")
        est_now = datetime.now(ZoneInfo("America/New_York"))
        f.write(f"Generated on: {est_now.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for i, article in enumerate(news_list, 1):
            f.write(f"Article {i}:\n")
            f.write(f"Title: {article['title']}\n")
            f.write(f"URL: {article['url']}\n")
            f.write(f"Source: {article['source']}\n")
            f.write(f"Author: {article['author']}\n")
            f.write(f"Timestamp: {article['timestamp']}\n")
            f.write("-" * 40 + "\n\n")
    return filepath

def send_txt_file_by_email(txt_filename, subject, recipient_email, gmail_creds_file="gmail.txt"):
    gmail_user, gmail_pass = read_gmail_credentials(gmail_creds_file)
    if not gmail_user or not gmail_pass:
        print("Missing Gmail credentials.")
        return
    try:
        with open(txt_filename, 'r', encoding='utf-8') as f:
            file_content = f.read()
    except Exception as e:
        print(f"Error reading file '{txt_filename}': {e}")
        return
    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(file_content, 'plain'))
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_user, gmail_pass)
            server.send_message(msg)
        print(f"✅ Email sent to {recipient_email} with file '{txt_filename}' content.")
    except Exception as e:
        print(f"❌ Error sending email: {e}")


# -------------------- Main --------------------

def main():
    api_key = read_api_key_from_file("serpapi_kira.txt")
    gmail_user, gmail_pass = read_gmail_credentials("gmail.txt")
    if not api_key or not gmail_user or not gmail_pass:
        print("❌ Missing required credentials.")
        return

    topics = read_file_lines("topics.txt")
    allowed_media = read_file_lines("media.txt")
    start_date, end_date = get_past_week_dates()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for topic in topics:
        print(f"\n🔍 Searching for: {topic}")
        raw_articles = get_news_by_keywords(api_key, topic, num_results=100,
                                            start_date_str=start_date, end_date_str=end_date)
        date_filtered = filter_articles_by_date(raw_articles, start_date, end_date)
        media_filtered = filter_articles_by_media(date_filtered, allowed_media)
        sorted_articles = sort_articles_by_source_and_date(media_filtered)

        # Save and send even if 0 articles
        txt_path = save_news_to_txt(sorted_articles, topic, timestamp)
        subject = f"({len(sorted_articles)}) Weekly News for '{topic}' ({start_date} to {end_date})"
        send_txt_file_by_email(txt_path, subject, "benjamin.joffe@sosv.com")
    #    send_txt_file_by_email(txt_path, subject, "kira.colburn@sosv.com")

        if sorted_articles:
            csv_filename = f"{timestamp}_{topic.replace(' ', '_')}.csv"
            save_news_to_csv(sorted_articles, topic, csv_filename)

if __name__ == "__main__":
    main()