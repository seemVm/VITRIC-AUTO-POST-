"""
Post one day's story frames as an IG story sequence, via the Instagram API (insta_poster).
This is the thing the GitHub Actions cron fires each day for hands-free story auto-upload.

    python post_stories.py <frames_folder>          # posts every NN_*.png in the folder, in order
    python post_stories.py <week_folder> --day 1_MON  # posts one day's subfolder

Needs the IG token in config.json (see GET-TOKEN.txt). Stories can't go through Vizard (video only);
they go through the official IG Content Publishing API (media_type=STORIES). No monthly cap.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import insta_poster

def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    folder = Path(sys.argv[1])
    if "--day" in sys.argv:
        folder = folder / sys.argv[sys.argv.index("--day") + 1]
    if not folder.is_dir():
        sys.exit(f"not a folder: {folder}")
    frames = sorted([p for p in folder.glob("*.png") if p.name[0].isdigit()]) or sorted(folder.glob("*.png"))
    if not frames:
        sys.exit(f"no story frames in {folder}")

    # --slot am|pm  ->  split the day per the story doctrine (spaced batches) AND kill dupes:
    # am = first half of the frames, pm = the rest. A committed .posted marker makes each
    # slot idempotent, so a re-run/double-fire can NEVER post the same frames twice.
    import datetime
    slot = None
    if "--slot" in sys.argv:
        slot = sys.argv[sys.argv.index("--slot") + 1]
    if slot in ("am", "pm"):
        marker = folder / f".posted_{datetime.date.today():%Y-%m-%d}_{slot}"
        if marker.exists():
            print(f"slot {slot} already posted today ({marker.name}) - skipping, no dupes.")
            return
        half = (len(frames) + 1) // 2
        frames = frames[:half] if slot == "am" else frames[half:]
        if not frames:
            print(f"nothing left for the {slot} slot - done.")
            marker.write_text("posted")
            return
        marker.write_text("posted")   # workflow commits this = permanent dedup

    # In CI (GitHub Actions): serve frames from GitHub's raw CDN (bulletproof) instead of a flaky free host.
    # Requires the repo to be PUBLIC so Meta can fetch the raw URLs. The token stays a secret regardless.
    import os
    repo = os.environ.get("GITHUB_REPOSITORY")
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    if repo:
        targets = [f"https://raw.githubusercontent.com/{repo}/{branch}/{f.as_posix()}" for f in frames]
        print(f"CI mode: serving {len(targets)} frames from GitHub raw CDN")
    else:
        targets = [str(f) for f in frames]
    print(f"posting {len(frames)} story frames from {folder.name} -> IG story...")
    ids = insta_poster.post_story(targets)
    print(f"DONE: posted {len(ids)}/{len(frames)} story frames")

if __name__ == "__main__":
    main()
