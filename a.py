import os
import requests
import feedparser
import subprocess
from pathlib import Path

# 定数
RSS_FEED_URL = "https://www.nhk.or.jp/s-media/news/podcast/list/v1/all.xml"
DOWNLOAD_DIR = "downloads"
ANALYSIS_CMD = "ffmpeg"

# フォルダの作成
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def fetch_rss_feed(url):
    """RSSフィードを取得する"""
    print(f"{url} からRSSフィードを取得中...")
    return feedparser.parse(url)

def download_mp3(feed_entries, download_dir):
    """MP3ファイルをダウンロードする（名前を変更せずに保存）"""
    downloaded_files = []
    print("MP3ファイルをダウンロード中...")

    for index, entry in enumerate(feed_entries, start=1):
        mp3_url = None
        for link in entry.links:
            if "audio" in link.type and link.href.endswith(".mp3"):
                mp3_url = link.href
                break

        if mp3_url:
            # URLから元のファイル名を抽出
            file_name = os.path.basename(mp3_url)
            file_path = Path(download_dir) / file_name

            print(f"ダウンロードリンク: {mp3_url}")  # デバッグ用出力
            print(f"保存予定ファイル名: {file_path}")  # デバッグ用出力

            try:
                response = requests.get(mp3_url)
                response.raise_for_status()
                with open(file_path, "wb") as f:
                    f.write(response.content)
                downloaded_files.append(file_path)
                print(f"{file_path} に保存しました。")
            except requests.RequestException as e:
                print(f"ダウンロード失敗: {mp3_url} - {e}")
        else:
            print(f"エントリ {index} にMP3リンクが見つかりませんでした。")

    return downloaded_files


def analyze_audio(file_path):
    """音声ファイルを解析する（最大音量と平均ラウドネス）"""
    print(f"ファイルを解析中: {file_path}")
    try:
        cmd = [
            ANALYSIS_CMD, "-i", str(file_path),
            "-af", "volumedetect",
            "-f", "null", "-"
        ]
        result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
        stderr_output = result.stderr

        max_volume = None
        mean_loudness = None
        for line in stderr_output.splitlines():
            if "max_volume:" in line:
                max_volume = float(line.split(":")[1].strip().replace(" dB", ""))
            elif "mean_volume:" in line:
                mean_loudness = float(line.split(":")[1].strip().replace(" dB", ""))
        return max_volume, mean_loudness
    except Exception as e:
        print(f"解析失敗: {e}")
        return None, None

# メイン処理
if __name__ == "__main__":
    feed = fetch_rss_feed(RSS_FEED_URL)

    print("各エントリのリンク情報を確認します...")
    if feed.entries:
        downloaded_files = download_mp3(feed.entries, DOWNLOAD_DIR)

        if downloaded_files:
            print("\nMP3ファイルの音量解析を開始します...\n")
            total_loudness = 0
            loudness_count = 0
            min_loudness = float("inf")
            max_loudness = float("-inf")

            for file in downloaded_files:
                max_volume, mean_loudness = analyze_audio(file)
                if max_volume is not None:
                    print(f"ファイル: {file.name}")
                    print(f"  最大音量: {max_volume:.2f} dB")
                    print(f"  平均ラウドネス: {mean_loudness:.2f} LUFS\n")
                    if mean_loudness is not None:
                        total_loudness += mean_loudness
                        loudness_count += 1
                        min_loudness = min(min_loudness, mean_loudness)
                        max_loudness = max(max_loudness, mean_loudness)
                else:
                    print(f"解析に失敗しました: {file.name}")

            # 全体の平均ラウドネスを計算
            if loudness_count > 0:
                overall_avg_loudness = total_loudness / loudness_count
                print("\n--- 結果 ---")
                print(f"ダウンロードしたMP3ファイル全体の平均ラウドネス: {overall_avg_loudness:.2f} LUFS")
                print(f"最高の平均ラウドネス: {max_loudness:.2f} LUFS")
                print(f"最低の平均ラウドネス: {min_loudness:.2f} LUFS")
            else:
                print("\nラウドネスのデータが取得できなかったため、平均を計算できません。")
        else:
            print("MP3ファイルがダウンロードされていません。")
    else:
        print("RSSフィードにMP3ファイルが見つかりませんでした。")
