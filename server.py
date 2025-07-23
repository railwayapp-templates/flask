# server.py
from flask import Flask, request, jsonify
import os
import librosa

app = Flask(__name__)

@app.route('/analyze', methods=['POST'])
def analyze():
    file = request.files['file']
    filename = file.filename
    filepath = os.path.join('uploads', filename)
    os.makedirs('uploads', exist_ok=True)
    file.save(filepath)

    # קריאת אודיו וניתוח בסיסי
    y, sr = librosa.load(filepath, sr=None)
    duration = librosa.get_duration(y=y, sr=sr)

    # דוגמה: זיהוי סוג ערוץ לפי שם
    if 'vocal' in filename.lower() or 'שירה' in filename:
        channel_type = 'Vocals'
    elif 'drum' in filename.lower() or 'תופים' in filename:
        channel_type = 'Drums'
    elif 'bass' in filename.lower() or 'בס' in filename:
        channel_type = 'Bass'
    elif 'guitar' in filename.lower() or 'גיטרה' in filename:
        channel_type = 'Guitar'
    elif 'piano' in filename.lower() or 'פסנתר' in filename:
        channel_type = 'Piano'
    else:
        channel_type = 'Unknown'

    # המלצות פלאגינים לפי סוג ערוץ
    plugin_suggestions = {
        'Vocals': ['EQ', 'De-Esser', 'Compressor', 'Reverb'],
        'Drums': ['EQ', 'Compressor', 'Transient Shaper'],
        'Bass': ['EQ', 'Compressor', 'Saturation'],
        'Guitar': ['EQ', 'Compressor', 'Chorus'],
        'Piano': ['EQ', 'Compressor', 'Reverb'],
        'Unknown': ['EQ', 'Compressor']
    }

    return jsonify({
        'channel_type': channel_type,
        'duration': duration,
        'plugins': plugin_suggestions.get(channel_type, ['EQ', 'Compressor'])
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
