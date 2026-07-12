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
    print(f"posting {len(frames)} story frames from {folder.name} -> IG story...")
    ids = insta_poster.post_story([str(f) for f in frames])
    print(f"DONE: posted {len(ids)}/{len(frames)} story frames")

if __name__ == "__main__":
    main()
