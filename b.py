import os
import subprocess
import json

# 入力フォルダと出力フォルダの設定
input_folder = "downloads"
output_folder = "output"  # 調整したMP3の保存先
os.makedirs(output_folder, exist_ok=True)

# 最大音量を確認する
def get_max_volume(filepath):
    command = [
        "ffmpeg", "-i", filepath, "-filter:a", "volumedetect",
        "-f", "null", "-"
    ]
    result = subprocess.run(command, stderr=subprocess.PIPE, text=True)
    for line in result.stderr.splitlines():
        if "max_volume:" in line:
            return float(line.split(":")[-1].strip().replace(" dB", ""))
    return None

# 音量を調整する
def adjust_volume(filepath, output_filepath, gain_db):
    command = [
        "ffmpeg", "-i", filepath, "-filter:a",
        f"volume={gain_db}dB", "-y", output_filepath
    ]
    subprocess.run(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

# ラウドネス情報を取得する
def get_loudness_info(filepath):
    command = [
        "ffmpeg", "-i", filepath, "-filter:a", "loudnorm=print_format=json",
        "-f", "null", "-"
    ]
    result = subprocess.run(command, stderr=subprocess.PIPE, text=True)
    
    json_data = ""  # JSONデータを格納する変数
    inside_json = False  # JSONの開始を検出するフラグ
    
    # ffmpegのstderr出力を行ごとに解析
    for line in result.stderr.splitlines():
        line = line.strip()
        if line.startswith("{"):  # JSONデータの開始
            inside_json = True
        if inside_json:
            json_data += line  # JSONデータを追加
        if line.endswith("}"):  # JSONデータの終了
            break

    # JSONデータが見つかったら解析
    if json_data:
        try:
            return json.loads(json_data)
        except json.JSONDecodeError as e:
            print(f"JSONDecodeError: {e}")
            print(f"解析できなかったデータ: {json_data}")
    return None


# 全体のラウドネスを記録するリスト
all_loudness_values = []

# ファイルを処理する
for filename in os.listdir(input_folder):
    if filename.endswith(".mp3"):
        input_path = os.path.join(input_folder, filename)
        print(f"ファイルを解析中: {filename}")
        
        # 最大音量を取得
        max_volume = get_max_volume(input_path)
        if max_volume is None:
            print(f"  最大音量を取得できませんでした: {filename}")
            continue
        
        print(f"  最大音量: {max_volume:.1f} dB")
        
        # 音量調整が必要か判定
        if -2.5 <= max_volume <= -1.0:
            print(f"  調整は不要です。このファイルはスキップされます: {filename}")
        else:
            gain = -1.0 - max_volume
            print(f"  調整を適用: {gain:.2f} dB")
            
            # 出力先のパス
            output_path = os.path.join(output_folder, filename)
            
            # 音量調整後のファイルを保存
            adjust_volume(input_path, output_path, gain)
            print(f"  調整後のファイルを保存しました: {output_path}")
            
            # ラウドネス情報を取得して表示
            loudness_info = get_loudness_info(output_path)
            if loudness_info:
                output_loudness = float(loudness_info["output_i"])
                all_loudness_values.append(output_loudness)
                print(f"  平均ラウドネス（output_i）: {output_loudness:.2f} LUFS")
            else:
                print(f"  ラウドネス情報を取得できませんでした: {output_path}")

# 全体の平均ラウドネス、最高ラウドネス、最低ラウドネスを計算
if all_loudness_values:
    overall_avg_loudness = sum(all_loudness_values) / len(all_loudness_values)
    max_loudness = max(all_loudness_values)
    min_loudness = min(all_loudness_values)
    
    print("\n=== 全体のラウドネス統計 ===")
    print(f"全体の平均ラウドネス: {overall_avg_loudness:.2f} LUFS")
    print(f"最高ラウドネス: {max_loudness:.2f} LUFS")
    print(f"最低ラウドネス: {min_loudness:.2f} LUFS")
else:
    print("\nラウドネス情報が取得できたファイルはありませんでした。")

print("\nすべてのファイルの処理が完了しました。")
