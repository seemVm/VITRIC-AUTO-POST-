"""
VITRIC direct Instagram poster - our own stack, no Metricool, free forever.
Uses the official Instagram Content Publishing API (Instagram Login / graph.instagram.com).
Dev mode on YOUR OWN account = no app review. Posts single image, carousel, or story.

The Graph API needs a PUBLIC image URL (it can't take a local file), so we auto-upload
each local PNG to a free host (catbox.moe, no account) and feed the API that link.

    python insta_poster.py story   "frames/01.png" "frames/02.png" ...        # a story sequence (each frame = 1 story)
    python insta_poster.py carousel "caption text" slide01.png slide02.png ... # one carousel feed post
    python insta_poster.py photo    "caption text" image.png                   # single feed photo

Config: config.json  -> { "ig_user_id": "...", "access_token": "..." }  (see GET-TOKEN.txt)
"""
import sys, json, time, os
from pathlib import Path
import requests

HERE = Path(__file__).parent
CFG  = HERE / "config.json"
GVER = "v21.0"
BASE = f"https://graph.instagram.com/{GVER}"   # Instagram Login API (pageless)

def cfg():
    if not CFG.exists():
        sys.exit("no config.json - run the GET-TOKEN.txt steps first, then paste ig_user_id + access_token.")
    c = json.loads(CFG.read_text())
    if not c.get("ig_user_id") or not c.get("access_token") or "PASTE" in c.get("access_token",""):
        sys.exit("config.json missing ig_user_id / access_token - see GET-TOKEN.txt.")
    return c

def host_image(path):
    """return a public direct URL the API can fetch. If given a URL already (e.g. a GitHub raw URL from CI), pass it through.
    Otherwise upload to a free host (UA header + 0x0.st fallback)."""
    if str(path).startswith(("http://", "https://")):
        return str(path)  # already a public URL (GitHub raw) - nothing to host
    path = Path(path)
    UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
    # try catbox
    try:
        with open(path, "rb") as f:
            r = requests.post("https://catbox.moe/user/api.php", data={"reqtype": "fileupload"},
                              files={"fileToUpload": (path.name, f)}, headers=UA, timeout=120)
        u = r.text.strip()
        if r.ok and u.startswith("http"):
            return u
    except Exception:
        pass
    # fallback: 0x0.st (reliable from datacenter IPs, needs a real UA)
    with open(path, "rb") as f:
        r = requests.post("https://0x0.st", files={"file": (path.name, f)}, headers=UA, timeout=120)
    r.raise_for_status()
    url = r.text.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"image host failed: {url}")
    return url

def _wait_ready(container_id, token, tries=20):
    """poll a container until it's FINISHED before publishing (safe for all media types)."""
    for _ in range(tries):
        r = requests.get(f"{BASE}/{container_id}",
                         params={"fields": "status_code", "access_token": token}, timeout=30).json()
        st = r.get("status_code")
        if st == "FINISHED": return
        if st == "ERROR": raise RuntimeError(f"container error: {r}")
        time.sleep(3)
    # images are usually instant; don't hard-fail if status field absent

def _create(ig, token, **params):
    params["access_token"] = token
    r = requests.post(f"{BASE}/{ig}/media", data=params, timeout=60).json()
    if "id" not in r: raise RuntimeError(f"container create failed: {r}")
    return r["id"]

def _publish(ig, token, creation_id):
    # retry on 9007 "media not ready" (container still processing) - wait + retry up to ~60s
    last = None
    for _ in range(12):
        r = requests.post(f"{BASE}/{ig}/media_publish",
                          data={"creation_id": creation_id, "access_token": token}, timeout=60).json()
        if "id" in r:
            return r["id"]
        last = r; err = r.get("error", {})
        if err.get("code") == 9007 or err.get("error_subcode") == 2207027 or err.get("is_transient"):
            time.sleep(5); continue
        raise RuntimeError(f"publish failed: {r}")
    raise RuntimeError(f"publish failed after retries (media never ready): {last}")

def post_reel(caption, video, c=None, share_to_feed=True):
    """post a REEL via the same free API. video = local path (hosted) or a public http(s) url
    (in CI we pass the GitHub raw CDN url). video processing is slower than images -> long waits."""
    c = c or cfg(); ig, tok = c["ig_user_id"], c["access_token"]
    url = video if str(video).startswith(("http://", "https://")) else host_image(video)
    print(f"  hosted -> {url}")
    cid = _create(ig, tok, media_type="REELS", video_url=url, caption=caption or "",
                  share_to_feed="true" if share_to_feed else "false")
    _wait_ready(cid, tok, tries=60)          # video transcode can take a few minutes
    mid = _publish(ig, tok, cid); print(f"  PUBLISHED reel id={mid}"); return mid

def post_photo(caption, image, c=None):
    c = c or cfg(); ig, tok = c["ig_user_id"], c["access_token"]
    url = host_image(image); print(f"  hosted -> {url}")
    cid = _create(ig, tok, image_url=url, caption=caption or "")
    _wait_ready(cid, tok)
    mid = _publish(ig, tok, cid); print(f"  PUBLISHED photo id={mid}"); return mid

def post_story(images, c=None):
    c = c or cfg(); ig, tok = c["ig_user_id"], c["access_token"]
    ids = []
    for img in images:
        url = host_image(img); print(f"  hosted -> {url}")
        cid = _create(ig, tok, image_url=url, media_type="STORIES")
        _wait_ready(cid, tok)
        mid = _publish(ig, tok, cid); print(f"  PUBLISHED story frame id={mid}")
        ids.append(mid)
        time.sleep(2)  # gentle spacing so frames stack in order
    return ids

def post_carousel(caption, images, c=None):
    c = c or cfg(); ig, tok = c["ig_user_id"], c["access_token"]
    if not (2 <= len(images) <= 10): sys.exit("carousel needs 2-10 images")
    children = []
    for img in images:
        url = host_image(img); print(f"  hosted -> {url}")
        cid = _create(ig, tok, image_url=url, is_carousel_item="true")
        _wait_ready(cid, tok); children.append(cid)
    parent = _create(ig, tok, media_type="CAROUSEL", caption=caption or "",
                     children=",".join(children))
    _wait_ready(parent, tok)
    mid = _publish(ig, tok, parent); print(f"  PUBLISHED carousel id={mid}"); return mid

if __name__ == "__main__":
    if len(sys.argv) < 3: sys.exit(__doc__)
    mode = sys.argv[1]
    if mode == "reel":
        post_reel(sys.argv[2], sys.argv[3])
    elif mode == "story":
        post_story(sys.argv[2:])
    elif mode == "carousel":
        post_carousel(sys.argv[2], sys.argv[3:])
    elif mode == "photo":
        post_photo(sys.argv[2], sys.argv[3])
    else:
        sys.exit(f"unknown mode '{mode}' - use reel | story | carousel | photo")
    print("done.")
