from __future__ import annotations

import argparse

from app.pipelines.content_pipeline import ContentPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI Content Factory pipeline once.")
    parser.add_argument("--channel", dest="channel_id", help="Optional channel_id to run.")
    args = parser.parse_args()

    pipeline = ContentPipeline.build()
    results = pipeline.run_once(channel_id=args.channel_id)
    for result in results:
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
