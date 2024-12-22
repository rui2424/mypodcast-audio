import os
import requests
import feedparser
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree
import subprocess

# 定数
RSS_FEED_URL = "https://www.nhk.or.jp/s-media/news/podcast/list/v1/all.xml"
OUTPUT_DIR = "output"
UPDATED_FEED_FILE = "updated_feed.xml"
GITHUB_PAGES_BASE_URL = "https://rui2424.github.io/mypodcast-audio/"  # 自分のGitHub Pages URLに置き換える

def fetch_rss_feed(url):
    """RSSフィードを取得する"""
    print(f"{url} からRSSフィードを取得中...")
    response = requests.get(url)
    response.raise_for_status()
    return feedparser.parse(response.content.decode("utf-8"))

def check_and_replace_files(feed_entries, output_dir):
    """RSS内のMP3ファイルとoutputフォルダ内のMP3を比較して置き換える"""
    replaced_files = []
    for entry in feed_entries:
        mp3_url = None
        for link in entry.links:
            if "audio" in link.type and link.href.endswith(".mp3"):
                mp3_url = link.href
                break

        if not mp3_url:
            continue  # MP3リンクがない場合はスキップ

        # MP3ファイル名を取得
        file_name = os.path.basename(mp3_url)
        output_file_path = Path(output_dir) / file_name

        if output_file_path.exists():
            print(f"調整済みファイルを発見: {output_file_path}")
            # GitHub PagesのURLを生成
            github_url = GITHUB_PAGES_BASE_URL + file_name
            # 置き換え対象としてリストに追加
            replaced_files.append((mp3_url, github_url))

    return replaced_files

def update_rss_feed(feed, replaced_files, output_file):
    """RSSフィードを更新して保存する"""
    root = Element("rss", attrib={"version": "2.0"})
    channel = SubElement(root, "channel")

    # RSS情報を作成
    for entry in feed.entries:
        item = SubElement(channel, "item")
        title = SubElement(item, "title")
        title.text = entry.title

        description = SubElement(item, "description")
        description.text = entry.get("description", "")

        link = SubElement(item, "link")
        link.text = entry.get("link", "リンクがありません")  # 修正済み

        # MP3リンクを修正
        mp3_url = None
        for link_info in entry.links:
            if "audio" in link_info.type and link_info.href.endswith(".mp3"):
                mp3_url = link_info.href
                break

        if mp3_url:
            # 置き換えリンクがあれば更新
            replaced_file = next((f[1] for f in replaced_files if f[0] == mp3_url), None)
            if replaced_file:
                new_link = SubElement(item, "enclosure", attrib={
                    "url": replaced_file,
                    "type": "audio/mpeg"
                })
            else:
                new_link = SubElement(item, "enclosure", attrib={
                    "url": mp3_url,
                    "type": "audio/mpeg"
                })

    # RSSフィードを保存
    tree = ElementTree(root)
    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    print(f"新しいRSSフィードを {output_file} に保存しました。")

def upload_to_github(file_path):
    """生成されたファイルをGitHubにアップロードする"""
    try:
        # 未追跡ファイルを含めてすべて追加
        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(["git", "commit", "-m", f"Update {file_path}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print(f"{file_path} をGitHubにアップロードしました。")
    except subprocess.CalledProcessError as e:
        print("GitHubへのアップロードに失敗しました:", e)

# メイン処理
if __name__ == "__main__":
    # RSSフィードを取得
    feed = fetch_rss_feed(RSS_FEED_URL)

    if feed.entries:
        # 調整済みファイルの確認と置き換え
        replaced_files = check_and_replace_files(feed.entries, OUTPUT_DIR)

        if replaced_files:
            print(f"{len(replaced_files)} 件の調整済みファイルをRSSフィードに反映します。")
            for original_url, adjusted_file in replaced_files:
                print(f"置き換え: {original_url} → {adjusted_file}")

            # RSSフィードを更新
            update_rss_feed(feed, replaced_files, UPDATED_FEED_FILE)

            # GitHubにアップロード
            upload_to_github(UPDATED_FEED_FILE)
        else:
            print("調整済みファイルは見つかりませんでした。")
    else:
        print("RSSフィード内にエントリが見つかりませんでした。")
