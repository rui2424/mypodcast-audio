import os
import hashlib
import requests
import xml.etree.ElementTree as ET
import subprocess
from pathlib import Path

# RSSフィードのURL
RSS_FEED_URL = "https://www.nhk.or.jp/s-media/news/podcast/list/v1/all.xml"
# 出力ディレクトリ
OUTPUT_DIR = Path("output")
DOWNLOADS_DIR = Path("downloads")
UPDATED_FEED_FILE = "updated_feed.xml"
REMOTE_URL = "https://github.com/<rui2424>/<mypodcast-audio>.git"  # リポジトリURLを設定してください

# ディレクトリの作成
OUTPUT_DIR.mkdir(exist_ok=True)
DOWNLOADS_DIR.mkdir(exist_ok=True)


def download_file(url, output_path):
    """指定したURLからファイルをダウンロード"""
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)


def calculate_hash(file_path):
    """ファイルのMD5ハッシュを計算"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def normalize_audio(input_file, output_file):
    """音声ファイルを正規化"""
    command = [
        "ffmpeg", "-i", input_file, "-af", "loudnorm", "-y", output_file
    ]
    subprocess.run(command, check=True)


def process_rss_feed():
    """RSSフィードを処理し、音声をダウンロード・正規化"""
    print(f"{RSS_FEED_URL} からRSSフィードを取得中...")
    response = requests.get(RSS_FEED_URL)
    response.raise_for_status()
    rss_feed = response.content

    root = ET.fromstring(rss_feed)
    namespace = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}

    processed_files = []
    for item in root.findall(".//item"):
        enclosure = item.find("enclosure")
        if enclosure is None:
            continue

        audio_url = enclosure.get("url")
        if not audio_url:
            continue

        file_name = audio_url.split("/")[-1]
        download_path = DOWNLOADS_DIR / file_name

        # ダウンロード
        if not download_path.exists():
            print(f"音声ファイルをダウンロード中: {audio_url}")
            download_file(audio_url, download_path)

        # ハッシュ計算
        audio_hash = calculate_hash(download_path)
        output_file = OUTPUT_DIR / f"{audio_hash}_{file_name}"

        # 正規化済みでない場合のみ処理
        if not output_file.exists():
            print(f"音声ファイルを正規化中: {download_path} → {output_file}")
            normalize_audio(download_path, output_file)
        else:
            print(f"調整済みファイルを発見: {output_file}")

        # URLの置き換え
        new_url = f"https://<rui2424>.github.io/<mypodcast-audio>/{output_file.name}"
        enclosure.set("url", new_url)
        processed_files.append(output_file)

    # 更新されたRSSフィードを保存
    tree = ET.ElementTree(root)
    tree.write(UPDATED_FEED_FILE, encoding="utf-8", xml_declaration=True)
    print(f"新しいRSSフィードを {UPDATED_FEED_FILE} に保存しました。")

    return processed_files


def upload_to_github():
    """GitHubに更新をプッシュ"""
    try:
        # リモートリポジトリの確認
        result = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True)
        if "origin" not in result.stdout:
            # リモートリポジトリを追加
            print(f"リモートリポジトリを設定中: {REMOTE_URL}")
            subprocess.run(["git", "remote", "add", "origin", REMOTE_URL], check=True)

        # 変更を追加してコミット
        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(["git", "commit", "-m", f"Update {UPDATED_FEED_FILE}"], check=True)

        # プッシュ（初回は-uオプションを追加）
        subprocess.run(["git", "push", "-u", "origin", "master"], check=True)
        print(f"GitHubにアップロードが完了しました。")
    except subprocess.CalledProcessError as e:
        print("GitHubへのアップロードに失敗しました:", e)


def main():
    """メイン関数"""
    try:
        processed_files = process_rss_feed()
        print(f"{len(processed_files)} 件の音声ファイルが処理されました。")
        upload_to_github()
    except Exception as e:
        print("エラーが発生しました:", e)


if __name__ == "__main__":
    main()
