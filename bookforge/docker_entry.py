"""Docker entrypoint: reads CHANNEL_URL from env and invokes the CLI."""

import os


def main() -> None:
    url = os.environ.get("CHANNEL_URL")
    if not url:
        # Fall through to normal CLI if no CHANNEL_URL (user passes as args)
        from bookforge.main import main as cli_main

        cli_main()
        return

    # Build argv as if user typed: bookforge <url>
    argv = [url]
    max_videos = os.environ.get("BOOKFORGE_MAX_VIDEOS")
    if max_videos:
        argv.extend(["--max-videos", max_videos])

    import asyncio

    from bookforge.main import parse_args, run

    args = parse_args(argv)
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
