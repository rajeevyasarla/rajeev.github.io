"""Build the 27-second homepage reel from existing synchronized comparisons."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "img/assets/MAPLE/MAPLE_vs_DeepSight_highlights.mp4"
POSTER = OUTPUT.with_suffix(".jpg")
MANIFEST = OUTPUT.with_suffix(".json")
FPS = 12
SEGMENTS = (
    ("25424", "construction_obstacles", 6, 15),
    ("27494", "blocked_intersection", 15, 24),
    ("28198", "left_turn_into_traffic", 35, 44),
)


def probe(path):
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ], text=True))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("comparison_directory", type=Path,
                        help="The existing visualization/MAPLE_vs_DeepSight directory")
    args = parser.parse_args()
    sources = [args.comparison_directory / f"MAPLE_vs_DeepSight_{case}_{name}.mp4"
               for case, name, _, _ in SEGMENTS]
    if any(path.exists() for path in (OUTPUT, POSTER, MANIFEST)):
        raise SystemExit("Refusing to overwrite an existing demo, poster, or manifest.")
    source_manifest = json.loads((args.comparison_directory / "comparison_manifest.json").read_text())
    cases = {case["case"]: case for case in source_manifest["cases"]}
    for source, (case, _, start, end) in zip(sources, SEGMENTS):
        info = probe(source)
        video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
        assert (video["width"], video["height"]) == (1920, 660)
        assert video["r_frame_rate"] == "12/1"
        assert float(info["format"]["duration"]) >= end > start
        assert cases[case]["playback_speed"] == 2
        assert cases[case]["start_simulation_s"] == 0
        assert cases[case]["layout"] == "MAPLE left / DeepSight right; front camera with BEV inset"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    filters = []
    for index, (_, _, start, end) in enumerate(SEGMENTS):
        filters.append(
            f"[{index}:v]trim=start_frame={start * FPS}:end_frame={end * FPS},"
            f"setpts=PTS-STARTPTS,setsar=1[v{index}]")
    filters.append("[v0][v1][v2]concat=n=3:v=1:a=0[out]")
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-n",
               "-filter_complex_threads", "2"]
    for source in sources:
        command.extend(["-threads", "2", "-i", str(source)])
    command.extend(["-filter_complex", ";".join(filters), "-map", "[out]", "-an",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-threads", "4", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    "-map_metadata", "-1", "-metadata", "title=MAPLE vs DeepSight: three scenario highlights"])
    with tempfile.TemporaryDirectory(prefix=".maple-demo-build-", dir=OUTPUT.parent) as temporary:
        temporary_video = Path(temporary) / OUTPUT.name
        subprocess.run(command + [str(temporary_video)], check=True)
        info = probe(temporary_video)
        video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
        duration = float(info["format"]["duration"])
        assert abs(duration - 27) < 1 / FPS and duration <= 30
        assert video["codec_name"] == "h264" and video["pix_fmt"] == "yuv420p"
        assert int(video["nb_frames"]) == 324
        assert temporary_video.stat().st_size < 20 * 1024 * 1024
        temporary_video.rename(OUTPUT)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-n",
                    "-ss", "6", "-i", str(OUTPUT), "-frames:v", "1", "-q:v", "2",
                    str(POSTER)], check=True)
    manifest = {
        "video": OUTPUT.name, "poster": POSTER.name,
        "duration_seconds": duration, "frame_rate": FPS,
        "dimensions": [1920, 660], "total_frames": 324,
        "playback_speed_vs_simulation": 2,
        "layout": "MAPLE left / DeepSight right; original front views and BEV insets",
        "same_elapsed_simulation_time": True,
        "edits": "Three continuous excerpts, hard cuts only; no extra speedup or motion interpolation.",
        "interpretation": "Selected simulated routes, not aggregate benchmark evidence. Incomplete DeepSight result statuses are not classified as failures.",
        "source_segments": [
            {"source": source.name, "source_sha256": sha256(source), "case": case,
             "scenario": name.replace("_", " "), "source_start_seconds": start,
             "source_end_seconds": end, "output_start_seconds": index * 9,
             "output_end_seconds": (index + 1) * 9,
             "nominal_simulation_start_seconds": start * 2,
             "nominal_simulation_end_seconds": end * 2}
            for index, (source, (case, name, start, end)) in enumerate(zip(sources, SEGMENTS))
        ],
        "video_sha256": sha256(OUTPUT), "poster_sha256": sha256(POSTER),
        "video_bytes": OUTPUT.stat().st_size,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"PASS: {duration:g}s; 1920x660 H.264; {OUTPUT.stat().st_size / 1024 / 1024:.2f} MiB")
    print(OUTPUT)


if __name__ == "__main__":
    main()
