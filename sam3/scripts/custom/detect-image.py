"""
detect-image.py — SAM3 image segmentation from text prompt

Usage (single image):
    python detect-image.py --prompt "bee" --input photo.jpg --out-dir ./out

Usage (folder):
    python detect-image.py --prompt "bee" --input-dir ./photos --out-dir ./out
    python detect-image.py --prompt "bee" --input-dir ./photos --out-dir ./out --recursive

Output per image:
    {image}_mask_{prompt}_{i}.png   original pixels inside mask, black background
    summary.json                    objects found: boxes, scores, files

Output for batch mode (in out-dir root):
    batch_summary.json              global recap across all images
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return slug or "prompt"


def clean_dir(path: Path):
    if path.exists() and any(path.iterdir()):
        print(f"Cleaning output dir: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def find_images(folder: Path, recursive: bool):
    pattern = "**/*" if recursive else "*"
    return sorted(p for p in folder.glob(pattern) if p.suffix.lower() in IMAGE_EXTENSIONS)


def process_image(prompt: str, img_path: Path, out: Path, model, processor_cls) -> dict:
    """Process a single image. Returns the summary dict."""
    from sam3.model.sam3_image_processor import Sam3Processor

    out.mkdir(parents=True, exist_ok=True)

    image = Image.open(img_path).convert("RGB")
    image_array = np.array(image)
    image_name = img_path.stem
    prompt_slug = slugify(prompt)

    processor = processor_cls(model)
    state = processor.set_image(image)
    result = processor.set_text_prompt(state=state, prompt=prompt)

    masks = result["masks"].cpu().numpy()
    boxes = result["boxes"].cpu().numpy()
    scores = result["scores"].cpu().numpy()

    objects = []
    for i, mask in enumerate(masks):
        binary = (np.squeeze(mask) > 0.5)
        masked = np.zeros_like(image_array)
        masked[binary] = image_array[binary]
        fname = f"{image_name}_mask_{prompt_slug}_{i}.png"
        Image.fromarray(masked).save(out / fname)
        objects.append({
            "index": i,
            "score": round(float(scores[i]), 4),
            "box": [round(v, 1) for v in boxes[i].tolist()],
            "file": fname,
        })

    summary = {
        "image": img_path.name,
        "prompt": prompt,
        "objects_found": len(objects),
        "objects": objects,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))

    print(f"  {img_path.name} — {len(objects)} object(s) found")
    return summary


def run(prompt: str, input_path: str, out_dir: str):
    from sam3.model_builder import build_sam3_image_model
    from sam3.model.sam3_image_processor import Sam3Processor

    img_path = Path(input_path)
    if not img_path.exists():
        sys.exit(f"Image not found: {input_path}")

    out = Path(out_dir)
    clean_dir(out)

    model = build_sam3_image_model()
    summary = process_image(prompt, img_path, out, model, Sam3Processor)

    print(f"Saved to {out.resolve()}")
    for obj in summary["objects"]:
        print(f"  [{obj['index']}] score={obj['score']:.3f}  box={obj['box']}")


def run_batch(prompt: str, input_dir: str, out_dir: str, recursive: bool):
    from sam3.model_builder import build_sam3_image_model
    from sam3.model.sam3_image_processor import Sam3Processor

    folder = Path(input_dir)
    if not folder.is_dir():
        sys.exit(f"Not a directory: {input_dir}")

    images = find_images(folder, recursive)
    if not images:
        sys.exit(f"No image files found in {input_dir}")

    print(f"Found {len(images)} image(s) to process")
    out_root = Path(out_dir)
    clean_dir(out_root)

    model = build_sam3_image_model()

    batch_results = []
    for i, img_path in enumerate(images, 1):
        rel = img_path.relative_to(folder).with_suffix("")
        img_out = out_root / rel
        print(f"[{i}/{len(images)}] {img_path.name}")
        summary = process_image(prompt, img_path, img_out, model, Sam3Processor)
        batch_results.append({
            "image": summary["image"],
            "path": str(img_path),
            "out_dir": str(img_out),
            "objects_found": summary["objects_found"],
            "summary_file": str(img_out / "summary.json"),
        })

    batch_summary = {
        "prompt": prompt,
        "input_dir": str(folder),
        "recursive": recursive,
        "total_images": len(images),
        "total_objects_found": sum(r["objects_found"] for r in batch_results),
        "images_with_detections": sum(1 for r in batch_results if r["objects_found"] > 0),
        "images": batch_results,
    }
    batch_path = out_root / "batch_summary.json"
    batch_path.write_text(json.dumps(batch_summary, indent=2))

    print(f"\n{'='*60}")
    print(f"Batch done — {len(images)} image(s) processed")
    print(f"  Total objects found   : {batch_summary['total_objects_found']}")
    print(f"  Images with detection : {batch_summary['images_with_detections']}/{len(images)}")
    print(f"  Batch summary         : {batch_path.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input", help="Single image file")
    input_group.add_argument("--input-dir", help="Folder of images to process")

    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--recursive", action="store_true", help="Search input-dir recursively for images")
    args = parser.parse_args()

    if args.input:
        run(args.prompt, args.input, args.out_dir)
    else:
        run_batch(args.prompt, args.input_dir, args.out_dir, args.recursive)
