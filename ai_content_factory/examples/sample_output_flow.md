# Sample Output Flow

This is the expected file flow after one successful run for `tech_facts_daily`.
Actual provider choice depends on availability:

- Script: Ollama or fallback
- Voice: Piper, Windows SAPI, or fallback
- Visuals: styled local card generator

## Command

```powershell
python -m app.run_once --channel tech_facts_daily
```

## Console result

```json
{
  "job": {
    "job_id": "tech_facts_daily-20260311170114-hidden-smartphone-featur",
    "channel_id": "tech_facts_daily",
    "topic": "Hidden smartphone features most people ignore",
    "status": "completed",
    "video_path": "output/videos/tech_facts_daily/tech_facts_daily-20260311170114-hidden-smartphone-featur.mp4"
  },
  "published": true
}
```

## Output tree

```text
output/
  scripts/tech_facts_daily/<job_id>_script.json
  scripts/tech_facts_daily/<job_id>_script.txt
  scenes/tech_facts_daily/<job_id>_scenes.json
  images/tech_facts_daily/<job_id>/scene_01.png
  images/tech_facts_daily/<job_id>/scene_02.png
  audio/tech_facts_daily/<job_id>/scene_01.wav
  audio/tech_facts_daily/<job_id>/scene_02.wav
  subtitles/tech_facts_daily/<job_id>.srt
  videos/tech_facts_daily/<job_id>.mp4
  metadata/tech_facts_daily/<job_id>_metadata.json
```

## Registry updates

```text
data/used_topics.json
data/published_videos.json
data/failed_jobs.json
```

`published_videos.json` gets the final job payload, metadata, upload records, and timestamp.
