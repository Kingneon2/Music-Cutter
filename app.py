import os, re, io, zipfile, tempfile, subprocess
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def safe(name):
    return re.sub(r'[\\/:*?"<>|]', '', name).strip()[:80] or "clip"

@app.get("/")
def home():
    return "OK"

@app.post("/split")
def split():
    data = request.get_json(force=True)
    url, clips = data.get("url"), data.get("clips")
    if not url or not clips:
        return jsonify(error="Missing url or clips"), 400

    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(
            ["yt-dlp", "-x", "--audio-format", "mp3",
             "-o", os.path.join(tmp, "audio.%(ext)s"), url],
            capture_output=True, text=True)
        if r.returncode != 0:
            return jsonify(error="Download failed: " + r.stderr[-200:]), 400

        full = os.path.join(tmp, "audio.mp3")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for i, c in enumerate(clips, 1):
                out = os.path.join(tmp, f"{i}.mp3")
                cmd = ["ffmpeg", "-y", "-i", full, "-ss", str(c["start"])]
                if c.get("end") is not None:
                    cmd += ["-t", str(c["end"] - c["start"])]
                cmd += ["-c:a", "libmp3lame", out]
                subprocess.run(cmd, capture_output=True)
                z.write(out, f"{i:02d} - {safe(c['title'])}.mp3")
        buf.seek(0)
        return send_file(buf, mimetype="application/zip",
                         download_name="clips.zip")
