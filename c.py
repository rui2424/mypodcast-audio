import os
import requests
import feedparser
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree
from datetime import datetime
import re

# 定数
RSS_FEED_URL = "https://www.nhk.or.jp/s-media/news/podcast/list/v1/all.xml"
OUTPUT_DIR = "output"
UPDATED_FEED_FILE = "updated_feed.xml"
ITUNES_IMAGE_URL = "https://example.com/podcast-cover.jpg"
ITUNES_CATEGORY = "News"

# フォルダの作成
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_rss_feed(url):
    """RSSフィードを取得する"""
    print(f"{url} からRSSフィードを取得中...")
    response = requests.get(url)
    response.raise_for_status()
    return feedparser.parse(response.content.decode("utf-8"))

def download_file(url, output_path):
    """ファイルを指定したURLからダウンロードする"""
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(output_path, "wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)
    print(f"ダウンロード完了: {output_path}")

def get_file_size(file_path):
    """ファイルサイズを取得する"""
    return os.path.getsize(file_path)

def format_pub_date(date_str):
    """RSS用のRFC 2822形式の日付を生成"""
    # '2024-12-22T12:00:00+09:00' のような形式を処理
    date = datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
    return date.strftime("%a, %d %b %Y %H:%M:%S +0900")

def update_rss_feed(feed, replaced_files, output_file):
    """RSSフィードを更新して保存する"""
    root = Element("rss", attrib={"version": "2.0", "xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"})
    channel = SubElement(root, "channel")

    # RSSの基本情報
    SubElement(channel, "title").text = "NHK Podcast"
    SubElement(channel, "link").text = "https://example.com"
    SubElement(channel, "language").text = "ja"
    SubElement(channel, "itunes:image", attrib={"href": ITUNES_IMAGE_URL})
    SubElement(channel, "itunes:category", attrib={"text": ITUNES_CATEGORY})
    SubElement(channel, "itunes:explicit").text = "no"

    for entry in feed.entries:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = entry.title
        SubElement(item, "description").text = entry.get("description", "")
        SubElement(item, "link").text = entry.get("link", "https://example.com")
        SubElement(item, "pubDate").text = format_pub_date(entry.get("published", datetime.now().isoformat()))

        mp3_url = None
        for link in entry.links:
            if "audio" in link.type and link.href.endswith(".mp3"):
                mp3_url = link.href
                break

        if mp3_url:
            replaced_file = next((f[1] for f in replaced_files if f[0] == mp3_url), None)
            if replaced_file:
                file_size = get_file_size(replaced_file)
                SubElement(item, "enclosure", attrib={
                    "url": str(replaced_file),
                    "type": "audio/mpeg",
                    "length": str(file_size)
                })
            else:
                SubElement(item, "enclosure", attrib={
                    "url": mp3_url,
                    "type": "audio/mpeg"
                })

    # RSSフィードを保存
    tree = ElementTree(root)
    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    print(f"新しいRSSフィードを {output_file} に保存しました。")

def check_and_download_files(feed_entries, output_dir):
    """RSS内のMP3ファイルをダウンロードして確認する"""
    replaced_files = []
    for entry in feed_entries:
        mp3_url = None
        for link in entry.links:
            if "audio" in link.type and link.href.endswith(".mp3"):
                mp3_url = link.href
                break

        if not mp3_url:
            continue

        file_name = os.path.basename(mp3_url)
        output_file_path = Path(output_dir) / file_name

        if not output_file_path.exists():
            print(f"ファイルをダウンロードします: {mp3_url}")
            download_file(mp3_url, output_file_path)

        replaced_files.append((mp3_url, output_file_path))

    return replaced_files

# メイン処理
if __name__ == "__main__":
    feed = fetch_rss_feed(RSS_FEED_URL)

    if feed.entries:
        replaced_files = check_and_download_files(feed.entries, OUTPUT_DIR)

        if replaced_files:
            print(f"{len(replaced_files)} 件のファイルをダウンロードまたは確認しました。")
            update_rss_feed(feed, replaced_files, UPDATED_FEED_FILE)
        else:
            print("ファイルのダウンロードや置き換えは行われませんでした。")
    else:
        print("RSSフィード内にエントリが見つかりませんでした。")
