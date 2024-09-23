import os
import tgt  # TextGridTools
import pandas as pd
from pydub import AudioSegment
import re
import sys # for logging

# Set the directory containing your audio and TextGrid files
audio_dir = 'audios'
segmented_dir = 'segmented_audios'
output_csv = 'segmented_audios.csv'
output_csv_time = 'segmented_audios_time.csv'
segments = []

# Define the pattern for "TB-L[x]" and "NTB-L[y]" (allow case-insensitivity, optional spaces)
pattern_tb_lx = re.compile(r'\s*tb\s*-\s*l(\d+)\s*', re.IGNORECASE)
#pattern_ntb_ly = re.compile(r'\s*ntb\s*-\s*l(\d+)\s*', re.IGNORECASE)
pattern_tb_lx_normal = re.compile(r'\s*tb\s*-\s*l(\d+)\s*-\s*normal\s*', re.IGNORECASE)
pattern_tb_docx = re.compile(r'\s*tb\s*-\s*doc(\d+)\s*', re.IGNORECASE)
pattern_tb_docx_normal = re.compile(r'\s*tb\s*-\s*doc(\d+)\s*-\s*normal\s*', re.IGNORECASE)

log_filename = 'log.txt'


class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout  # Save the original stdout
        self.log_file = open(filename, "w")  # Open the log file

    def write(self, message):
        self.terminal.write(message)  # Write to console
        self.log_file.write(message)  # Write to the log file

    def flush(self):
        # This is needed for compatibility with some environments
        self.terminal.flush()
        self.log_file.flush()


def create_segments(tier, tier_name, audio, filename, normalized_tier=None):
    for interval in tier.intervals:
        normalized_interval_text = ""

        if(normalized_tier):
            normalized_intervals = normalized_tier.get_annotations_between_timepoints(interval.start_time, interval.end_time)

            for normalized_interval in normalized_intervals:
                normalized_interval_text += normalized_interval.text + " "

        # Skip empty intervals
        if normalized_tier and normalized_interval_text == "":
            continue
        if interval.text == ""  or interval.text == "...":
            continue

        start_time = interval.start_time * 1000  # convert to milliseconds
        end_time = interval.end_time * 1000  # convert to milliseconds
        segment = audio[start_time:end_time]

        # Create a directory for the segmented audio if it doesn't exist
        segment_dir = os.path.join(segmented_dir, os.path.splitext(filename)[0])
        os.makedirs(segment_dir, exist_ok=True)

        # Create a new filename for the segmented audio
        segment_filename = f"{os.path.splitext(filename)[0]}_seg_{interval.start_time:.2f}_{interval.end_time:.2f}.wav"
        segment_path = os.path.join(segment_dir, segment_filename)

        # Export the segmented audio
        segment.export(segment_path, format='wav')


        
        append_to_csv(segment_filename, filename, tier_name, interval, normalized_interval_text)


def append_to_csv(segment_filename, filename, tier_name, interval, normalized_interval_text=None):
    # Append to segments list
    segments.append({
        'path': os.path.splitext(filename)[0] + "/" + segment_filename,
        'name': os.path.splitext(filename)[0],
        'speaker': os.path.splitext(filename)[0] + "_" + tier_name,
        'start_time': interval.start_time,
        'end_time': interval.end_time,
        'normalized_text': normalized_interval_text if normalized_interval_text else None,
        'text': interval.text
    })


def process_file(filename):
    wav_path = os.path.join(audio_dir, filename)
    tg_path = os.path.splitext(wav_path)[0] + '.TextGrid'

    # Try reading the .TextGrid file (case-sensitive)
    try:
        tg = tgt.io.read_textgrid(tg_path)  # Default attempt with .TextGrid
    except (UnicodeDecodeError, FileNotFoundError):
        # If .TextGrid fails, try with .textgrid
        tg_path = os.path.splitext(wav_path)[0] + '.textgrid'
        try:
            tg = tgt.io.read_textgrid(tg_path)
        except UnicodeDecodeError:
            # If utf-8 fails, attempt with utf-16 encoding
            try:
                with open(tg_path, 'r', encoding='utf-16') as f:
                    tg = tgt.io.read_textgrid(f)
            except Exception as e:
                print(f"Error reading {tg_path} with utf-16: {e}")
                return
        except Exception as e:
            print(f"Error reading {tg_path}: {e}")
            return
    except Exception as e:
        print(f"Error reading {tg_path}: {e}")
        return

    # Get the names of all tiers in the TextGrid
    tier_names = tg.get_tier_names()

    tb_l_tiers = {}  # Dictionary to store TB-L[x] tiers
    #ntb_l_tiers = {}  # Dictionary to store NTB-L[y] tiers
    tb_l_normal_tiers = {}  # Dictionary to store TB-L[x]-normal tiers
    tb_doc_1_tiers = {}
    tb_doc_1_normal_tiers = {}

    # Find all tiers matching "TB-L[x]" and "NTB-L[y]"
    for tier_name in tier_names:
        tb_match = pattern_tb_lx.fullmatch(tier_name.strip())
        #ntb_match = pattern_ntb_ly.fullmatch(tier_name.strip())
        tb_normal_match = pattern_tb_lx_normal.fullmatch(tier_name.strip())
        tb_doc_match = pattern_tb_docx.fullmatch(tier_name.strip())
        tb_doc_normal_match = pattern_tb_docx_normal.fullmatch(tier_name.strip())

        if tb_match:
            x = int(tb_match.group(1))
            if x >= 1:
                tb_l_tiers[x] = tg.get_tier_by_name(tier_name)
                print(f"Found TB-L{x} tier '{tier_name}' in {tg_path}.")

        if tb_normal_match:
            x = int(tb_normal_match.group(1))
            if x >= 1:
                tb_l_normal_tiers[x] = tg.get_tier_by_name(tier_name)
                print(f"Found TB-L{x}-normal tier '{tier_name}' in {tg_path}.")

        if tb_doc_match:
            x = int(tb_doc_match.group(1))
            if x >= 1:
                tb_doc_1_tiers[x] = tg.get_tier_by_name(tier_name)
                print(f"Found TB-DOC{x} tier '{tier_name}' in {tg_path}.")

        if tb_doc_normal_match:
            x = int(tb_doc_normal_match.group(1))
            if x >= 1:
                tb_doc_1_normal_tiers[x] = tg.get_tier_by_name(tier_name)
                print(f"Found TB-DOC{x}-normal tier '{tier_name}' in {tg_path}.")


    # Load the audio file
    print(f"Processing {filename}...")
    audio = AudioSegment.from_wav(wav_path)

    # Segment audio based on "TB-L[x]" tiers
    for x, tb_tier in tb_l_tiers.items():
        # If there is a corresponding "TB-L[x]-normal" tier, use it to segment the audio
        if x in tb_l_normal_tiers:
            tb_normal_tier = tb_l_normal_tiers[x]
            create_segments(tb_tier, f"TB-L{x}", audio, filename, tb_normal_tier)
        else:
            print(f"ERROR: No TB-L{x}-normal tier found for TB-L{x} tier in {tg_path}. Audio: {filename}")
            create_segments(tb_tier, f"TB-L{x}", audio, filename)


    for x, tb_tier in tb_doc_1_tiers.items():
        # If there is a corresponding "TB-L[x]-normal" tier, use it to segment the audio
        if x in tb_doc_1_normal_tiers:
            tb_normal_tier = tb_doc_1_normal_tiers[x]
            create_segments(tb_tier, f"TB-DOC{x}", audio, filename, tb_normal_tier)
        else:
            print(f"ERROR: No TB-DOC{x}-normal tier found for TB-DOC{x} tier in {tg_path}. Audio: {filename}")
            create_segments(tb_tier, f"TB-DOC{x}", audio, filename)


def segmentate_audio():
    for filename in os.listdir(audio_dir):
        if filename.endswith('.wav'):
            print(f"/---- Processing {filename} ----/")
            process_file(filename)
            print(f"/---- Processed {filename}, Processing next file ----/")

    # Create a DataFrame and save to CSV
    df = pd.DataFrame(segments)
    # Assuming your DataFrame is called df
    df_time = df.sort_values(by=['name', 'start_time'], ascending=[True, True])
    df.to_csv(output_csv, index=False)
    df_time.to_csv(output_csv_time, index=False)
    print(f"Segments saved to {output_csv}.")
    print(f"Segments saved to {output_csv_time}.")


logger = Logger(log_filename)

# Redirect stdout to the custom logger
sys.stdout = logger

segmentate_audio()

# Restore the original stdout when done
sys.stdout = logger.terminal
logger.log_file.close()

print("Log file created: ", log_filename)