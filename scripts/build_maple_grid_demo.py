"""Build a RoCA-format 3-row × 2-column MAPLE comparison, lasting 20 seconds."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

from build_maple_demo import FPS, ROOT, probe, sha256

OUTPUT = ROOT / "img/assets/MAPLE/MAPLE_vs_DeepSight_3x2.mp4"
POSTER = OUTPUT.with_suffix(".jpg")
MANIFEST = OUTPUT.with_suffix(".json")
SEGMENTS = (
    ("25424", "construction_obstacles", "Construction obstacles", 9, 29),
    ("27494", "blocked_intersection", "Blocked intersection", 3, 23),
    ("28198", "left_turn_into_traffic", "Left turn into traffic", 23, 43),
)
FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


def label_overlay(path, case, title):
    """Add RoCA-style method badges and a centered scenario label."""
    overlay = Image.new("RGBA", (1920, 540), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    method_font = ImageFont.truetype(str(FONT), 36)
    case_font = ImageFont.truetype(str(FONT), 24)
    speed_font = ImageFont.truetype(str(FONT), 18)
    for column, method, color in ((0, "MAPLE", "#23b85b"), (1, "DeepSight", "#ee8828")):
        x = 16 + column * 960
        width = draw.textlength(method, font=method_font)
        draw.rounded_rectangle((x, 5, x + width + 20, 50), radius=6, fill=color)
        draw.text((x + 10, 5), method, font=method_font, fill="white")
        draw.text((column * 960 + 878, 20), "2×", font=speed_font, fill="white")
    # Keep the grid divider behind the centered caption, as in RoCA.
    draw.line((960, 0, 960, 539), fill="white", width=3)
    draw.line((0, 539, 1919, 539), fill=(255, 255, 255, 190), width=2)
    label = f"{case} · {title}"
    width = draw.textlength(label, font=case_font)
    x = (1920 - width - 24) / 2
    draw.rounded_rectangle((x, 496, x + width + 24, 536), radius=6, fill=(15, 20, 25, 230))
    draw.text((x + 12, 501), label, font=case_font, fill="white")
    overlay.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("comparison_directory", type=Path)
    args = parser.parse_args()
    sources = [args.comparison_directory / f"MAPLE_vs_DeepSight_{case}_{slug}.mp4"
               for case, slug, _, _, _ in SEGMENTS]
    if any(path.exists() for path in (OUTPUT, POSTER, MANIFEST)):
        raise SystemExit("Refusing to overwrite existing grid assets.")
    source_manifest = json.loads((args.comparison_directory / "comparison_manifest.json").read_text())
    cases = {case["case"]: case for case in source_manifest["cases"]}
    reference = probe(ROOT / "img/assets/RoCA/RoCA_vs_ORION_all_scenarios_vertical.mp4")
    reference_video = next(stream for stream in reference["streams"] if stream["codec_type"] == "video")
    assert (reference_video["width"], reference_video["height"]) == (1920, 1620)
    assert float(reference["format"]["duration"]) == 20
    for source, (case, _, _, start, end) in zip(sources, SEGMENTS):
        info = probe(source)
        video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
        assert (video["width"], video["height"]) == (1920, 660)
        assert video["r_frame_rate"] == "12/1"
        assert float(info["format"]["duration"]) >= end and end - start == 20
        assert cases[case]["playback_speed"] == 2
        assert cases[case]["start_simulation_s"] == 0
        assert cases[case]["layout"] == "MAPLE left / DeepSight right; front camera with BEV inset"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".maple-grid-build-", dir=OUTPUT.parent) as temporary:
        temporary = Path(temporary)
        overlays = []
        for index, (case, _, title, _, _) in enumerate(SEGMENTS):
            overlay = temporary / f"labels-{index}.png"
            label_overlay(overlay, case, title)
            overlays.append(overlay)
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-n",
                   "-filter_complex_threads", "2"]
        for source in sources:
            command.extend(["-threads", "2", "-i", str(source)])
        for overlay in overlays:
            command.extend(["-i", str(overlay)])
        filters = []
        for index, (_, _, _, start, end) in enumerate(SEGMENTS):
            filters.append(
                f"[{index}:v]trim=start_frame={start * FPS}:end_frame={end * FPS},"
                f"setpts=PTS-STARTPTS,crop=1920:540:0:60,setsar=1[view{index}]")
            filters.append(f"[view{index}][{index + 3}:v]overlay=eof_action=repeat:format=auto[row{index}]")
        filters.append("[row0][row1][row2]vstack=inputs=3:shortest=1[out]")
        video_path = temporary / OUTPUT.name
        command.extend(["-filter_complex", ";".join(filters), "-map", "[out]", "-an",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                        "-threads", "4", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        "-map_metadata", "-1", "-metadata", "title=MAPLE vs DeepSight: 3x2 scenario comparison",
                        str(video_path)])
        subprocess.run(command, check=True)
        info = probe(video_path)
        video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
        assert float(info["format"]["duration"]) == 20
        assert (video["width"], video["height"]) == (1920, 1620)
        assert video["codec_name"] == "h264" and video["pix_fmt"] == "yuv420p"
        assert int(video["nb_frames"]) == 240
        assert video_path.stat().st_size < 20 * 1024 * 1024
        video_path.rename(OUTPUT)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-ss", "6",
                    "-i", str(OUTPUT), "-frames:v", "1", "-q:v", "2", str(POSTER)], check=True)
    manifest = {
        "video": OUTPUT.name, "poster": POSTER.name, "duration_seconds": 20,
        "frame_rate": FPS, "total_frames": 240, "dimensions": [1920, 1620],
        "grid_rows": 3, "grid_columns": 2, "row_dimensions": [1920, 540],
        "method_columns": ["MAPLE", "DeepSight"], "reference_format": "RoCA: 1920x1620, 20 seconds",
        "playback_speed_vs_simulation": 2, "same_elapsed_simulation_time_per_method_pair": True,
        "edits": "Three continuous 20-second excerpts shown simultaneously. Crop removes each source's separate outer title/footer bands, not its driving panel. No image scaling, extra speedup, or motion interpolation. RoCA-style method/scenario badges added.",
        "interpretation": "Selected simulated routes, not aggregate benchmark evidence. Different rows have different start times; methods within each row remain synchronized. Incomplete DeepSight result statuses are not classified as failures.",
        "source_segments": [
            {"source": source.name, "source_sha256": sha256(source), "case": case,
             "scenario": title, "grid_row": index + 1, "source_start_seconds": start,
             "source_end_seconds": end, "output_start_seconds": 0, "output_end_seconds": 20,
             "nominal_simulation_start_seconds": start * 2, "nominal_simulation_end_seconds": end * 2,
             "crop": {"x": 0, "y": 60, "width": 1920, "height": 540}}
            for index, (source, (case, _, title, start, end)) in enumerate(zip(sources, SEGMENTS))
        ],
        "video_sha256": sha256(OUTPUT), "poster_sha256": sha256(POSTER),
        "video_bytes": OUTPUT.stat().st_size,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"PASS: 20s; 3x2 grid; 1920x1620 H.264; {OUTPUT.stat().st_size / 1024 / 1024:.2f} MiB")
    print(OUTPUT)


if __name__ == "__main__":
    main()
