from flask import Flask, request, render_template,send_file,redirect,url_for,session
from flask_sqlalchemy import SQLAlchemy
import os
import sounddevice as sd
import librosa
import numpy as np
import soundfile as sf
import pandas as pd
import uuid
import pyaudio
import wave
from sys import byteorder
from array import array
from struct import pack


app = Flask(__name__)
app.secret_key = "BN@#LFANSN"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
app.app_context().push()

class users(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    Gender = db.Column(db.String(10))
    Nationality = db.Column(db.String(100))

    def __init__(self,Gender,Nationality):
        self.Gender = Gender
        self.Nationality = Nationality
class sentences(db.Model):
    recording_name = db.Column(db.String(100),primary_key=True)
    sentence = db.Column(db.String(100))

    def __init__(self,recording_name,sentence):
        self.recording_name = recording_name
        self.sentence = sentence


text_df = pd.read_csv("Madar_same_100.csv")

@app.route('/',methods=["POST","GET"])
def home():
    if request.method == "POST":
        gender = request.form["gender"]
        session["gender"] = gender
        nationality = request.form["nationality"]
        session["nationality"] = nationality
        usr = users(gender,nationality)
        db.session.add(usr)
        db.session.commit()
        session["id"] = usr._id
        return redirect(url_for('index'))
    else:
        return render_template('home.html')

@app.route('/record_page')
def index():
    nationality = session["nationality"]  # counterpart for url_for()
    random_ten = text_df[text_df["Nationality"] == nationality].sample(n=10)
    random_text = random_ten.Sentence.tolist()
    #session["sentence_id"] = random_ten.Sentence_id.tolist()
    return render_template('index.html',text=random_text)


@app.route("/view")
def view():
    return render_template("view.html",values=users.query.all() )

@app.route('/record', methods=['POST'])
def record():
    id = session["id"]
    nationality = session["nationality"] 
    #sentence_id = session["sentence_id"]
    sample_rate = 16000
    channels = 1

    filename = f'{id}_{nationality}_{uuid.uuid4()}.wav'
    session["filename"] = filename
    record_to_file(filename)

    # myrecording = sd.rec(int(10 * sample_rate), samplerate=sample_rate, channels=channels)
    # sd.wait()

    # sf.write(filename, myrecording, sample_rate)

    #return redirect(url_for('play', filename=filename))
    return 'Recording saved to file: {}'.format(filename)
    


@app.route('/play', methods=['GET'])
def play():
    filename = session["filename"]
    #sound = AudioSegment.from_file(filename, format='wav')
    #sound.export('recording.mp3', format='mp3')
    return send_file(filename, mimetype='audio/wav')

@app.route('/delete',methods=['GET'])
def delete():
    filename = session["filename"]
    os.remove(filename)
    return f"{filename} deleted"




THRESHOLD = 500
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
RATE = 16000

SILENCE = 30

def is_silent(snd_data):
    "Returns 'True' if below the 'silent' threshold"
    return max(snd_data) < THRESHOLD

def normalize(snd_data):
    "Average the volume out"
    MAXIMUM = 16384
    times = float(MAXIMUM)/max(abs(i) for i in snd_data)

    r = array('h')
    for i in snd_data:
        r.append(int(i*times))
    return r

def trim(snd_data):
    "Trim the blank spots at the start and end"
    def _trim(snd_data):
        snd_started = False
        r = array('h')

        for i in snd_data:
            if not snd_started and abs(i)>THRESHOLD:
                snd_started = True
                r.append(i)

            elif snd_started:
                r.append(i)
        return r

    # Trim to the left
    snd_data = _trim(snd_data)

    # Trim to the right
    snd_data.reverse()
    snd_data = _trim(snd_data)
    snd_data.reverse()
    return snd_data

def add_silence(snd_data, seconds):
    "Add silence to the start and end of 'snd_data' of length 'seconds' (float)"
    r = array('h', [0 for i in range(int(seconds*RATE))])
    r.extend(snd_data)
    r.extend([0 for i in range(int(seconds*RATE))])
    return r

def record():
    """
    Record a word or words from the microphone and 
    return the data as an array of signed shorts.
    Normalizes the audio, trims silence from the 
    start and end, and pads with 0.5 seconds of 
    blank sound to make sure VLC et al can play 
    it without getting chopped off.
    """
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=1, rate=RATE,
        input=True, output=True,
        frames_per_buffer=CHUNK_SIZE)

    num_silent = 0
    snd_started = False

    r = array('h')

    while 1:
        # little endian, signed short
        snd_data = array('h', stream.read(CHUNK_SIZE))
        if byteorder == 'big':
            snd_data.byteswap()
        r.extend(snd_data)

        silent = is_silent(snd_data)

        if silent and snd_started:
            num_silent += 1
        elif not silent and not snd_started:
            snd_started = True

        if snd_started and num_silent > SILENCE:
            break

    sample_width = p.get_sample_size(FORMAT)
    stream.stop_stream()
    stream.close()
    p.terminate()

    r = normalize(r)
    r = trim(r)
    r = add_silence(r, 0.5)
    return sample_width, r

def record_to_file(path):
    "Records from the microphone and outputs the resulting data to 'path'"
    sample_width, data = record()
    data = pack('<' + ('h'*len(data)), *data)

    wf = wave.open(path, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(sample_width)
    wf.setframerate(RATE)
    wf.writeframes(data)
    wf.close()





if __name__ == '__main__':
    db.create_all()
    app.run(debug=True, port=os.getenv("PORT", default=5000))
