# Vitric auto-post (private)
Fully-automated IG story posting via the official Instagram API + GitHub Actions cron.
SETUP: add repo secrets IG_USER_ID + IG_TOKEN (Settings -> Secrets -> Actions). Never commit the token.
WEEKLY: render locally (story_week.py) -> upload the story-week/<day>/ frames here -> the cron posts them 9a+1p ET.
Full guide: VITRIC-CONTENT-SYSTEM/16_AUTO-POST-API/STORY-AUTOPOST-SETUP.md
