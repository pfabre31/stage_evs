"""
detect-videos.py — SAM3 video segmentation from text prompt

Usage (single video):
    python detect-video.py --prompt "bee" --input video.mp4 --out-dir ./out
    python detect-video.py --prompt "bee" --input video.mp4 --out-dir ./out --step 30

Usage (folder):
    python detect-video.py --prompt "bee" --input-dir ./videos --out-dir ./out
    python detect-video.py --prompt "bee" --input-dir ./videos --out-dir ./out --recursive

Output per video (in a subfolder named after the video):
    {video}_{mask}_{prompt}_frame{N}_obj{id}.png   original pixels inside mask, black background
    summary.json                                    per-video recap

Output for batch mode (in out-dir root):
    batch_summary.json                              global recap across all videos
"""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


def extract_frames(video_path: Path, step: int):
    import cv2
    tmp = Path(tempfile.mkdtemp(prefix="sam3_frames_"))
    cap = cv2.VideoCapture(str(video_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration_s = round(total / fps, 2) if fps else None
    saved = 0
    for i in range(total):
        ret, frame = cap.read()
        if not ret:
            break
        if i % step == 0:
            cv2.imwrite(str(tmp / f"{saved:05d}.jpg"), frame)
            saved += 1
    cap.release()
    print(f"Extracted {saved} frames (1 every {step}) from {total} total — {fps:.2f} fps, {duration_s}s")
    return tmp, fps, duration_s


def masked_image(frame_path: Path, mask: np.ndarray) -> np.ndarray:
    """Original RGB pixels where mask is True, black elsewhere."""
    frame = np.array(Image.open(frame_path).convert("RGB"))
    result = np.zeros_like(frame)
    result[mask.astype(bool)] = frame[mask.astype(bool)]
    return result


def process_video(prompt: str, src: Path, out: Path, step: int, predictor) -> dict:
    """Process a single video file. Returns the summary dict."""
    video_name = src.stem
    prompt_slug = prompt.replace(" ", "_")
    out.mkdir(parents=True, exist_ok=True)

    tmp_dir = None
    resource = src
    video_fps = None
    video_duration_s = None
    if src.suffix.lower() in VIDEO_EXTENSIONS:
        tmp_dir, video_fps, video_duration_s = extract_frames(src, step)
        resource = tmp_dir

    response = predictor.handle_request(dict(
        type="start_session",
        resource_path=str(resource),
    ))
    session_id = response["session_id"]

    predictor.handle_request(dict(
        type="add_prompt",
        session_id=session_id,
        frame_index=0,
        text=prompt,
    ))
    print(f"  Prompt '{prompt}' set on frame 0, propagating...")

    all_obj_ids = set()
    summary_frames = []
    total_frames_processed = 0

    for frame_output in predictor.handle_stream_request(dict(
        type="propagate_in_video",
        session_id=session_id,
    )):
        total_frames_processed += 1
        frame_idx = frame_output["frame_index"]
        outputs = frame_output["outputs"]

        masks = outputs["out_binary_masks"]
        obj_ids = outputs["out_obj_ids"]
        scores = outputs.get("out_probs", [None] * len(obj_ids))

        frame_path = resource / f"{frame_idx:05d}.jpg"

        frame_objects = []
        for i, (obj_id, mask) in enumerate(zip(obj_ids, masks)):
            fname = f"{video_name}_mask_{prompt_slug}_frame{frame_idx:04d}_obj{obj_id}.png"
            if frame_path.exists():
                img = masked_image(frame_path, mask)
            else:
                img = mask.astype(np.uint8) * 255
            Image.fromarray(img).save(out / fname)

            all_obj_ids.add(int(obj_id))
            frame_objects.append({
                "obj_id": int(obj_id),
                "score": round(float(scores[i]), 4) if scores[i] is not None else None,
                "file": fname,
            })

        if frame_objects:
            summary_frames.append({
                "frame_index": frame_idx,
                "n_objects": len(frame_objects),
                "objects": frame_objects,
            })

        print(f"    frame {frame_idx:04d} — {len(obj_ids)} object(s)")

    predictor.handle_request(dict(type="close_session", session_id=session_id))

    if tmp_dir:
        shutil.rmtree(tmp_dir)

    effective_fps = round(video_fps / step, 2) if video_fps else None
    total_masks = sum(f["n_objects"] for f in summary_frames)

    summary = {
        "video": src.name,
        "prompt": prompt,
        "video_fps": round(video_fps, 2) if video_fps else None,
        "video_duration_s": video_duration_s,
        "step": step,
        "effective_fps": effective_fps,
        "total_frames_processed": total_frames_processed,
        "frames_with_detections": len(summary_frames),
        "total_mask_images": total_masks,
        "tracked_objects_count": len(all_obj_ids),
        "tracked_obj_ids": sorted(all_obj_ids),
        "frames": summary_frames,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))

    print(f"  Done — {total_masks} masks, {len(all_obj_ids)} tracked object(s) over {len(summary_frames)} frames")
    return summary


def clean_dir(path: Path):
    if path.exists() and any(path.iterdir()):
        print(f"Cleaning output dir: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def find_videos(folder: Path, recursive: bool):
    pattern = "**/*" if recursive else "*"
    return sorted(p for p in folder.glob(pattern) if p.suffix.lower() in VIDEO_EXTENSIONS)


def run(prompt: str, input_path: str, out_dir: str, step: int):
    from sam3.model_builder import build_sam3_video_predictor

    src = Path(input_path)
    if not src.exists():
        sys.exit(f"Input not found: {input_path}")

    clean_dir(Path(out_dir))
    predictor = build_sam3_video_predictor()
    process_video(prompt, src, Path(out_dir), step, predictor)
    print(f"\nSaved to {Path(out_dir).resolve()}")


def run_batch(prompt: str, input_dir: str, out_dir: str, step: int, recursive: bool):
    from sam3.model_builder import build_sam3_video_predictor

    folder = Path(input_dir)
    if not folder.is_dir():
        sys.exit(f"Not a directory: {input_dir}")

    videos = find_videos(folder, recursive)
    if not videos:
        sys.exit(f"No video files found in {input_dir}")

    print(f"Found {len(videos)} video(s) to process")
    out_root = Path(out_dir)
    clean_dir(out_root)

    predictor = build_sam3_video_predictor()

    batch_results = []
    for i, video in enumerate(videos, 1):
        rel = video.relative_to(folder).with_suffix("")
        video_out = out_root / rel
        print(f"\n[{i}/{len(videos)}] {video.name}")
        summary = process_video(prompt, video, video_out, step, predictor)
        batch_results.append({
            "video": summary["video"],
            "path": str(video),
            "out_dir": str(video_out),
            "video_fps": summary["video_fps"],
            "video_duration_s": summary["video_duration_s"],
            "total_frames_processed": summary["total_frames_processed"],
            "frames_with_detections": summary["frames_with_detections"],
            "total_mask_images": summary["total_mask_images"],
            "tracked_objects_count": summary["tracked_objects_count"],
            "tracked_obj_ids": summary["tracked_obj_ids"],
            "summary_file": str(video_out / "summary.json"),
        })

    batch_summary = {
        "prompt": prompt,
        "step": step,
        "input_dir": str(folder),
        "recursive": recursive,
        "total_videos": len(videos),
        "total_frames_processed": sum(r["total_frames_processed"] for r in batch_results),
        "total_frames_with_detections": sum(r["frames_with_detections"] for r in batch_results),
        "total_mask_images": sum(r["total_mask_images"] for r in batch_results),
        "total_tracked_objects": sum(r["tracked_objects_count"] for r in batch_results),
        "videos": batch_results,
    }
    batch_path = out_root / "batch_summary.json"
    out_root.mkdir(parents=True, exist_ok=True)
    batch_path.write_text(json.dumps(batch_summary, indent=2))

    print(f"\n{'='*60}")
    print(f"Batch done — {len(videos)} video(s) processed")
    print(f"  Total frames analysed : {batch_summary['total_frames_processed']}")
    print(f"  Total masks saved     : {batch_summary['total_mask_images']}")
    print(f"  Batch summary         : {batch_path.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input", help="Single MP4/MOV/AVI/MKV file or JPEG folder")
    input_group.add_argument("--input-dir", help="Folder of videos to process")

    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--step", type=int, default=1, help="Process 1 frame every N (default: 1 = all frames)")
    parser.add_argument("--recursive", action="store_true", help="Search input-dir recursively for videos")
    args = parser.parse_args()

    if args.input:
        run(args.prompt, args.input, args.out_dir, args.step)
    else:
        run_batch(args.prompt, args.input_dir, args.out_dir, args.step, args.recursive)
