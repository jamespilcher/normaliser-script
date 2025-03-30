import os
import subprocess
from pydub import AudioSegment
import json
import re

# === SETTINGS ===
TARGET_I = -16.0  # Integrated loudness in LUFS
TARGET_TP = -1.5  # True peak in dB
TARGET_LRA = 11.0  # Loudness range
INPUT_FOLDER = "input"
OUTPUT_FOLDER = "output"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# === Function to normalize using loudnorm ===
def normalize_audio(input_path, output_path):
    # First pass - measure loudness
    measure_cmd = [
        "ffmpeg", "-i", input_path, "-af",
        f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json",
        "-f", "null", "-"
    ]
    result = subprocess.run(measure_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    matches = re.findall(r"\{[\s\S]*?\}", result.stderr)
    loudness_data = json.loads(matches[-1]) if matches else None

    if not loudness_data:
        print(f"Could not read loudness data from {input_path}")
        return

    # Second pass - apply normalization
    norm_filter = (
        f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:"
        f"measured_I={loudness_data['input_i']}:"
        f"measured_TP={loudness_data['input_tp']}:"
        f"measured_LRA={loudness_data['input_lra']}:"
        f"measured_thresh={loudness_data['input_thresh']}:"
        f"offset={loudness_data['target_offset']}:linear=true:print_format=summary"
    )

    norm_cmd = [
        "ffmpeg", "-i", input_path, "-af", norm_filter,
        "-ar", "44100", "-y", output_path
    ]
    subprocess.run(norm_cmd)

# === Main Loop ===
for filename in os.listdir(INPUT_FOLDER):
    if not filename.lower().endswith(('.mp3', '.wav', '.flac', '.m4a')):
        continue

    input_path = os.path.join(INPUT_FOLDER, filename)
    temp_wav = os.path.join(INPUT_FOLDER, f"{os.path.splitext(filename)[0]}_converted.wav")

    # Convert to WAV first
    audio = AudioSegment.from_file(input_path)
    audio.export(temp_wav, format="wav")

    # Normalize
    output_path = os.path.join(OUTPUT_FOLDER, f"{os.path.splitext(filename)[0]}_normalized.wav")
    normalize_audio(temp_wav, output_path)

    # Clean up
    os.remove(temp_wav)
    print(f"✅ Normalized: {filename}")

print("\nAll files processed.")
