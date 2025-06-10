#!/usr/bin/env python3
"""
Script to overlay detection bounding boxes and top matches on a video based on a .matches JSON file.
Each unique trackletId is assigned a consistent bright color, and the top matches for each track are displayed
at the top-right corner of its bounding box on each frame.
"""
import cv2
import json
import argparse
import random


def get_top_matches_map(data, detections):
    """
    Build a mapping from trackletId to its list of top matches.
    Assumes `data['similarities']` provides one entry per unique trackletId, in the same order
    as sorted list of unique trackletIds from detections.
    """
    track_ids = sorted({det['trackletId'] for det in detections})
    similarities = data.get('similarities', [])
    if len(similarities) != len(track_ids):
        raise ValueError(
            f"Number of similarity entries ({len(similarities)}) does not match number of track IDs ({len(track_ids)})"
        )
    # Map each track to its matchList
    return {track_ids[i]: similarities[i].get('matchList', []) for i in range(len(track_ids))}


def assign_colors(track_ids):
    """
    Assign a bright, consistent BGR color to each trackletId.
    """
    random.seed(42)
    colors = {}
    for tid in track_ids:
        # Bright colors: each channel between 128 and 255
        colors[tid] = (
            random.randint(128, 255),
            random.randint(128, 255),
            random.randint(128, 255)
        )
    return colors


def main():
    parser = argparse.ArgumentParser(
        description="Overlay detection boxes and matches on video frames"
    )
    parser.add_argument(
        "matches_file", help="Path to the .matches JSON file"
    )
    parser.add_argument(
        "input_video", help="Path to the input video file"
    )
    parser.add_argument(
        "output_video", help="Path to save the annotated output video"
    )
    parser.add_argument(
        "--top", type=int, default=3,
        help="Number of top matches to display per track (default: 3)"
    )
    args = parser.parse_args()

    # Load matches JSON
    with open(args.matches_file, 'r') as f:
        data = json.load(f)

    # Extract detections
    detect_reply = data.get('detectReply', {})
    detections = detect_reply.get('detections', [])
    if not detections:
        print("No detections found in matches file.")
        return

    # Build frame-to-detections mapping
    frames = {}
    for det in detections:
        frame_num = det.get('frame', 0)
        frames.setdefault(frame_num, []).append(det)

    # Map top matches for each trackletId
    track_matches = get_top_matches_map(data, detections)

    # Assign colors
    track_ids = list(track_matches.keys())
    track_colors = assign_colors(track_ids)

    # Open video
    cap = cv2.VideoCapture(args.input_video)
    if not cap.isOpened():
        raise IOError(f"Cannot open video {args.input_video}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(
        args.output_video, fourcc, fps, (width, height)
    )

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    thickness = 1

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Overlay boxes for this frame
        if frame_idx in frames:
            for det in frames[frame_idx]:
                loc = det['location']
                x1, y1 = int(loc['x']), int(loc['y'])
                x2 = x1 + int(loc['width'])
                y2 = y1 + int(loc['height'])
                tid = det['trackletId']
                color = track_colors.get(tid, (0, 255, 0))

                # Draw rectangle
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                # Prepare match text
                matches = track_matches.get(tid, [])
                top_matches = [m.get('subjectIdGallery', '') for m in matches[:args.top]]
                text = ", ".join(top_matches)

                # Calculate text size and position at top-right of box
                (text_w, text_h), baseline = cv2.getTextSize(
                    text, font, font_scale, thickness
                )
                # try above box
                tx = x2 - text_w
                ty = y1 - 5
                if ty - text_h < 0:
                    # if too close to top, put below box
                    ty = y2 + text_h + 5

                # Draw text background for readability
                cv2.rectangle(
                    frame,
                    (tx, ty - text_h - baseline),
                    (tx + text_w, ty + baseline),
                    (0, 0, 0),
                    cv2.FILLED
                )
                # Put text
                cv2.putText(
                    frame, text, (tx, ty), font, font_scale, (255, 255, 255), thickness
                )

        # Write annotated frame
        out.write(frame)
        frame_idx += 1

    cap.release()
    out.release()
    print(f"Processing complete. Annotated video saved to {args.output_video}")


if __name__ == '__main__':
    main()
