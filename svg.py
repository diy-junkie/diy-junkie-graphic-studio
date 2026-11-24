
from flask import Flask, request, send_file, render_template_string, jsonify
from PIL import Image, ImageOps
from collections import Counter
from pathlib import Path
from io import BytesIO
import colorsys
import json
import uuid
import os
import math

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "junkie_graphic_data"
UPLOAD_DIR = DATA_DIR / "uploads"
SVG_DIR = DATA_DIR / "svg"
HISTORY_FILE = DATA_DIR / "history.json"

for folder in (DATA_DIR, UPLOAD_DIR, SVG_DIR):
    folder.mkdir(parents=True, exist_ok=True)

ALLOWED = {"png", "jpg", "jpeg", "webp", "bmp"}

HTML = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DIY JUNKIE GRAPHIC STUDIO</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#111827;color:#e5e7eb;font-family:Arial,sans-serif}
header{padding:20px;background:#0b1220;border-bottom:1px solid #334155}
header h2{margin:0;color:#60a5fa;letter-spacing:1px}
header p{color:#94a3b8;font-size:13px}
main{max-width:1100px;margin:auto;padding:16px}
.panel{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:16px;margin-bottom:16px}
h3{margin-top:0;color:#93c5fd}
label{display:block;margin:13px 0 6px;font-size:14px}
input,select,button{width:100%;padding:12px;border-radius:8px;border:1px solid #475569;background:#0f172a;color:white}
input[type=range]{padding:0}
button{background:#2563eb;border:0;font-weight:bold;margin-top:12px;cursor:pointer}
button:disabled{opacity:.5}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px}
.preview{background:#fff;border-radius:10px;min-height:250px;display:flex;align-items:center;justify-content:center;overflow:auto;padding:10px}
.preview img{max-width:100%;max-height:500px;object-fit:contain}
#svgPreview{width:100%;max-height:550px}
.small{font-size:12px;color:#94a3b8}
.row{display:flex;justify-content:space-between;gap:10px}
.row span{color:#60a5fa}
.download{background:#059669}
.secondary{background:#475569}
#status{padding:10px;color:#fbbf24;white-space:pre-wrap}
.historyItem{padding:10px;border-bottom:1px solid #475569;display:flex;justify-content:space-between;gap:10px;align-items:center}
.historyItem button{width:auto;margin:0;padding:8px}
</style>
</head>
<body>
<header>
<h2>DIY JUNKIE GRAPHIC STUDIO</h2>
<p>IMAGE TO SVG VECTOR CONVERTER · LOCAL EDITION</p>
</header>

<main>
<div class="panel">
<h3>01 / Import Image</h3>
<input type="file" id="file" accept="image/png,image/jpeg,image/webp,image/bmp">
<p class="small">Supported: PNG / JPG / JPEG / WEBP / BMP · Max 20 MB</p>
<div class="grid">
<div>
<label>Original Image</label>
<div class="preview"><img id="original" style="display:none"></div>
</div>
<div>
<label>Vector Preview</label>
<div class="preview" id="svgPreview">SVG Preview</div>
</div>
</div>
</div>

<div class="panel">
<h3>02 / Vector Settings</h3>
<div class="grid">
<div>
<label>Color Count: <span id="colorVal">8</span></label>
<input type="range" id="colors" min="2" max="24" value="8">
<label>Detail Level: <span id="detailVal">2</span></label>
<input type="range" id="detail" min="1" max="5" value="2">
<label>Image Width (px)</label>
<input type="number" id="width" min="32" max="1200" value="500">
</div>
<div>
<label>Background</label>
<select id="background">
<option value="white">White</option>
<option value="transparent">Transparent</option>
<option value="black">Black</option>
</select>
<label>Color Mode</label>
<select id="mode">
<option value="color">Full Color</option>
<option value="gray">Grayscale</option>
<option value="mono">Black & White</option>
</select>
<label>Path Smoothing</label>
<select id="smooth">
<option value="2">Normal</option>
<option value="1">High Detail</option>
<option value="4">Smooth</option>
</select>
</div>
</div>
<button id="convert">CONVERT TO SVG</button>
<div id="status"></div>
<button id="download" class="download" style="display:none">DOWNLOAD SVG</button>
<button id="png" class="secondary" style="display:none">DOWNLOAD PNG</button>
</div>

<div class="panel">
<h3>03 / Project History</h3>
<div id="history"><span class="small">Loading...</span></div>
</div>
</main>

<script>
let currentFile=null;
let currentId=null;

const $=id=>document.getElementById(id);

$("colors").oninput=()=> $("colorVal").textContent=$("colors").value;
$("detail").oninput=()=> $("detailVal").textContent=$("detail").value;

$("file").onchange=e=>{
 const f=e.target.files[0];
 if(!f)return;
 currentFile=f;
 currentId=null;
 $("original").src=URL.createObjectURL(f);
 $("original").style.display="block";
 $("svgPreview").textContent="Ready to convert";
 $("download").style.display="none";
 $("png").style.display="none";
 $("status").textContent="Image loaded: "+f.name;
};

$("convert").onclick=async()=>{
 if(!currentFile){$("status").textContent="Please select an image.";return;}
 $("convert").disabled=true;
 $("status").textContent="Converting... Please wait.";
 const fd=new FormData();
 fd.append("image",currentFile);
 fd.append("colors",$("colors").value);
 fd.append("detail",$("detail").value);
 fd.append("width",$("width").value);
 fd.append("background",$("background").value);
 fd.append("mode",$("mode").value);
 fd.append("smooth",$("smooth").value);
 try{
  const res=await fetch("/convert",{method:"POST",body:fd});
  const data=await res.json();
  if(!res.ok)throw new Error(data.error||"Conversion failed");
  currentId=data.id;
  $("svgPreview").innerHTML=data.svg;
  $("status").textContent="Conversion successful! Colors: "+data.colors+
   " | SVG size: "+data.bytes+" bytes";
  $("download").style.display="block";
  $("png").style.display="block";
  loadHistory();
 }catch(err){$("status").textContent="Error: "+err.message;}
 $("convert").disabled=false;
};

$("download").onclick=()=>{
 if(currentId)location.href="/download/"+currentId;
};
$("png").onclick=()=>{
 if(currentId)location.href="/png/"+currentId;
};

async function loadHistory(){
 try{
  const r=await fetch("/history");
  const items=await r.json();
  $("history").innerHTML="";
  if(!items.length){$("history").textContent="No projects yet.";return;}
  items.forEach(item=>{
   const div=document.createElement("div");
   div.className="historyItem";
   const name=document.createElement("span");
   name.textContent=item.name+" · "+item.date;
   const btn=document.createElement("button");
   btn.textContent="SVG";
   btn.onclick=()=>location.href="/download/"+item.id;
   div.append(name,btn);
   $("history").append(div);
  });
 }catch(e){$("history").textContent="History unavailable";}
}
loadHistory();
</script>
</body>
</html>
"""

def load_history():
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_history(items):
    HISTORY_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def hex_color(rgb):
    return "#%02x%02x%02x" % tuple(rgb[:3])

def simplify_points(points, tolerance):
    if len(points) <= 4:
        return points

    result = [points[0]]
    for p in points[1:]:
        last = result[-1]
        if math.hypot(p[0]-last[0], p[1]-last[1]) >= tolerance:
            result.append(p)

    if result[-1] != points[-1]:
        result.append(points[-1])
    return result

def boundary_paths(mask, w, h):
    """
    Trace pixel boundaries using horizontal scan runs.
    Each connected horizontal run becomes a closed SVG path.
    """
    paths = []
    for y in range(h):
        x = 0
        while x < w:
            if not mask[y*w+x]:
                x += 1
                continue

            start = x
            while x < w and mask[y*w+x]:
                x += 1
            end = x

            paths.append(
                f"M{start},{y} H{end} V{y+1} H{start} Z"
            )
    return paths

def make_svg(image, color_count, detail, width, background, mode, smooth):
    image = ImageOps.exif_transpose(image).convert("RGBA")

    # Composite transparent pixels against chosen background.
    if background == "black":
        base = Image.new("RGBA", image.size, (0,0,0,255))
    else:
        base = Image.new("RGBA", image.size, (255,255,255,255))

    if background == "transparent":
        # Keep transparent pixels transparent in the source processing.
        pass
    else:
        image = Image.alpha_composite(base, image)

    max_width = max(32, min(1200, int(width)))
    ratio = max_width / image.width
    new_size = (max_width, max(1, round(image.height * ratio)))
    image = image.resize(new_size, Image.Resampling.LANCZOS)

    if mode == "gray":
        image = ImageOps.grayscale(image).convert("RGB")
    elif mode == "mono":
        image = ImageOps.grayscale(image)
        image = image.point(lambda p: 255 if p > 128 else 0).convert("RGB")
    else:
        image = image.convert("RGB")

    # Reduce palette to a manageable number of colors.
    quantized = image.quantize(
        colors=max(2, min(24, int(color_count))),
        method=Image.Quantize.MEDIANCUT
    ).convert("RGB")

    pixels = list(quantized.getdata())
    palette = Counter(pixels)
    selected = [c for c, _ in palette.most_common(color_count)]

    w, h = quantized.size
    total = w*h
    paths_out = []

    for color in selected:
        mask = [1 if p == color else 0 for p in pixels]
        if not any(mask):
            continue

        # Pixel-run paths are robust on Android and require no OpenCV.
        paths = boundary_paths(mask, w, h)
        if not paths:
            continue

        color_path = " ".join(paths)
        paths_out.append(
            f'<path fill="{hex_color(color)}" d="{color_path}"/>'
        )

    bg_rect = ""
    if background == "white":
        bg_rect = f'<rect width="{w}" height="{h}" fill="#ffffff"/>'
    elif background == "black":
        bg_rect = f'<rect width="{w}" height="{h}" fill="#000000"/>'

    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'{bg_rect}'
        + "".join(paths_out) +
        '</svg>'
    )
    return svg, len(selected), (w,h)

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/convert", methods=["POST"])
def convert():
    try:
        file = request.files.get("image")
        if not file or not file.filename:
            return jsonify(error="No image selected"), 400

        ext = file.filename.rsplit(".",1)[-1].lower()
        if ext not in ALLOWED:
            return jsonify(error="Unsupported image format"), 400

        image = Image.open(file.stream)
        image.load()

        svg, used_colors, size = make_svg(
            image,
            int(request.form.get("colors",8)),
            int(request.form.get("detail",2)),
            int(request.form.get("width",500)),
            request.form.get("background","white"),
            request.form.get("mode","color"),
            int(request.form.get("smooth",2))
        )

        project_id = uuid.uuid4().hex[:12]
        svg_path = SVG_DIR / f"{project_id}.svg"
        svg_path.write_text(svg, encoding="utf-8")

        history = load_history()
        history.insert(0,{
            "id":project_id,
            "name":Path(file.filename).name,
            "date":__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
            "colors":used_colors,
            "size":size
        })
        save_history(history[:50])

        return jsonify(
            id=project_id,
            svg=svg,
            colors=used_colors,
            bytes=len(svg.encode("utf-8"))
        )
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route("/download/<project_id>")
def download_svg(project_id):
    path = SVG_DIR / f"{project_id}.svg"
    if not path.exists():
        return "SVG not found", 404
    return send_file(path, as_attachment=True, download_name="junkie_vector.svg")

@app.route("/png/<project_id>")
def download_png(project_id):
    path = SVG_DIR / f"{project_id}.svg"
    if not path.exists():
        return "SVG not found", 404

    # PNG rendering is not included because Pillow cannot render arbitrary SVG.
    return (
        "PNG export needs an SVG renderer. "
        "Open the SVG in a browser or vector editor and export as PNG.",
        501
    )

@app.route("/history")
def history():
    return jsonify(load_history())

if __name__ == "__main__":
    print("="*45)
    print(" DIY JUNKIE GRAPHIC STUDIO")
    print(" Open browser: http://127.0.0.1:5000")
    print("="*45)
    app.run(host="127.0.0.1", port=5000, debug=False)
