"""Reels queue poster (runs in GitHub Actions on the cron).
Queue layout: reels-queue/<YYYY-MM-DD>_<am|pm>/  containing  clip.mp4 + caption.txt
Each run posts the folder matching TODAY + the current slot (am = the 14:00 UTC run,
pm = the 22:00 UTC run), via the free IG Content Publishing API (media_type=REELS),
serving the video from GitHub's raw CDN (same pattern as the story cron).
After a successful post the folder is MOVED to reels-posted/ (the workflow commits the
move) so a re-run can never double-post. No folder due = clean exit 0.
"""
import os, sys, datetime, shutil

sys.path.insert(0, os.path.dirname(__file__))
from insta_poster import post_reel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "reels-queue")
POSTED = os.path.join(ROOT, "reels-posted")

def raw_url(path_in_repo):
    repo = os.environ["GITHUB_REPOSITORY"]           # e.g. seemVm/VITRIC-AUTO-POST-
    return f"https://raw.githubusercontent.com/{repo}/main/{path_in_repo}"

def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    slot = "am" if now.hour < 18 else "pm"           # 14:00 UTC run -> am, 22:00 UTC -> pm
    want = f"{now:%Y-%m-%d}_{slot}"
    if not os.path.isdir(QUEUE):
        print("no reels-queue folder. nothing to post."); return
    due = [d for d in sorted(os.listdir(QUEUE)) if d == want]
    # also catch missed past slots (cron delays / downtime): post the OLDEST overdue one instead
    if not due:
        overdue = [d for d in sorted(os.listdir(QUEUE)) if d < want]
        due = overdue[:1]
        if due: print(f"no exact match for {want}; posting overdue {due[0]}")
    if not due:
        print(f"nothing due for {want}. queue has: {sorted(os.listdir(QUEUE))}"); return
    folder = due[0]
    fdir = os.path.join(QUEUE, folder)
    clip = os.path.join(fdir, "clip.mp4")
    capf = os.path.join(fdir, "caption.txt")
    if not os.path.exists(clip):
        print(f"SKIP {folder}: no clip.mp4"); return
    caption = open(capf, encoding="utf-8").read().strip() if os.path.exists(capf) else ""
    url = raw_url(f"reels-queue/{folder}/clip.mp4")
    print(f"posting reel {folder} ...")
    mid = post_reel(caption, url)
    print(f"DONE: reel {folder} published id={mid}")
    os.makedirs(POSTED, exist_ok=True)
    shutil.move(fdir, os.path.join(POSTED, folder))   # workflow commits this move = dedup

if __name__ == "__main__":
    main()
