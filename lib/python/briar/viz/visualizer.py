#!/usr/bin/env python3
"""
Module: display_process.py
Defines DisplayProcess (a multiprocessing.Process) that caches and shows detected bounding boxes with matches,
and DisplayManager, a higher-level wrapper that manages frame/match buffering and playback.
"""
import cv2
import json
import random
import numpy as np
from multiprocessing import Process, Queue


def assign_colors(track_ids):
    random.seed(42)
    colors = {}
    for tid in track_ids:
        colors[tid] = (
            random.randint(128, 255),
            random.randint(128, 255),
            random.randint(128, 255)
        )
    return colors


def build_frame_mapping(detections):
    frames = {}
    for det in detections:
        frame_num = det.get('frame', 0)
        frames.setdefault(frame_num, []).append(det)
    return frames


def build_track_matches(data, detections):
    track_ids = sorted({d['trackletId'] for d in detections})
    sims = data.get('similarities', [])
    if len(sims) != len(track_ids):
        if len(track_ids) == 0 or len(sims) == 0:
            return {}
        raise ValueError(f"Sims length {len(sims)} != tracks {len(track_ids)}")
    return {track_ids[i]: sims[i].get('matchList', [])
            for i in range(len(track_ids))}


def extract_chip(frame, location):
    x = int(location['x'])
    y = int(location['y'])
    w = int(location['width'])
    h = int(location['height'])
    return frame[y:y+h, x:x+w]


def overlay_detections_on_frame(frame, detections, track_colors, track_matches, all_detections, top_n=3):
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.5
    thick = 1
    chips = []
    used_tracklets = set()

    for det in detections:
        loc = det['location']
        if 'x' not in loc or 'y' not in loc:
            continue
        x1, y1 = int(loc['x']), int(loc['y'])
        x2, y2 = x1 + int(loc['width']), y1 + int(loc['height'])
        tid = det['trackletId']
        color = track_colors.get(tid, (0, 255, 0))
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        matches = track_matches.get(tid, [])[:top_n]

        final_matches = []

        for match in matches:
            score = match["score"]
            if score >= 12.16448763 and score < 17.16266139:
                final_matches.append(match.get('subjectIdGallery', '') + " (LOW)")
            elif score >= 17.16266139 and score < 22.12316833:
                final_matches.append(match.get('subjectIdGallery', '') + " (MED)")
            elif score >= 22.12316833:
                final_matches.append(match.get('subjectIdGallery', '') + " (HIGH)")

        if len(final_matches) == 0:
            text = "no matches"
        else:
            text = ", ".join(final_matches)

        textColor = (255,255,255)
        textBackgroundColor = (0, 0, 0)

        (tw, th), bl = cv2.getTextSize(text, font, scale, thick)
        tx = x2 - tw
        ty = y1 - 5 if y1 - 5 - th >= 0 else y2 + th + 5

        cv2.rectangle(frame, (tx, ty - th - bl), (tx + tw, ty + bl), textBackgroundColor, cv2.FILLED)
        cv2.putText(frame, text, (tx, ty), font, scale, textColor, thick)

        if tid not in used_tracklets:
            candidates = [d for d in all_detections if d['trackletId'] == tid and 'x' in d and 'y' in d]
            if candidates:
                best_det = max(candidates, key=lambda d: d.get('confidence', 0))
                chip_loc = best_det.get('location')
                chip = extract_chip(frame, chip_loc)
                chips.append((chip, color))
                used_tracklets.add(tid)
    return chips


class DisplayProcess(Process):
    """Background process handling frame & match caching and display."""
    def __init__(self):
        super().__init__()
        self.queue = Queue()
        self.chip_map = {}

    def load_matches(self, json_str):
        data = json.loads(json_str)
        dets = data.get('detectReply', {}).get('detections', [])
        self.detections = dets
        self.match_map = build_track_matches(data, dets)
        self.frame_map = build_frame_mapping(dets)
        self.colors = assign_colors(self.match_map.keys())
        self.chip_map = {}

    def load_frames(self, frames):
        # frames: list of (idx, ndarray)
        self.frames = frames

    def clear_cache(self):
        self.frames = []
        self.detections = []
        self.match_map = {}
        self.frame_map = {}
        self.colors = {}
        self.chip_map = {}

    def show_display(self, top_n=3, wait_per_frame_ms=600):
        # print('all matches:', self.match_map[list(self.match_map.keys())[0]])
        # print('all frame idxs:', self.frame_map.keys())
        chip_height = 80
        chip_width = 60
        margin = 10
        

        for idx, frame in sorted(self.frames, key=lambda x: x[0]):
            # print('idx loop:', idx)
            dets = self.frame_map.get(idx, [])
            print('got frame:', idx, 'with detections:', len(dets))
            chips = overlay_detections_on_frame(frame, dets, self.colors, self.match_map, self.detections, top_n)
            strip_width = (chip_width + margin) * len(chips)
            strip = 255 * np.ones((chip_height + 2 * margin, strip_width, 3), dtype=np.uint8)
            if chips:
                for i, (chip, color) in enumerate(chips):
                    resized = cv2.resize(chip, (chip_width, chip_height))
                    x = i * (chip_width + margin) + margin
                    strip[margin:margin+chip_height, x:x+chip_width] = resized
                    cv2.rectangle(strip, (x, margin), (x+chip_width, margin+chip_height), color, 2)
                    # print('chip fame size:',chip.shape)
                frame_h, frame_w = frame.shape[:2]
                strip_h, strip_w = strip.shape[:2]
                if strip_w < frame_w:
                    pad_width = frame_w - strip_w
                    strip = cv2.copyMakeBorder(strip, 0, 0, 0, pad_width, cv2.BORDER_CONSTANT, value=(255, 255, 255))

                # combined = cv2.vconcat([frame, strip])
                # cv2.imshow('Matches Display', combined)
            else:
                pass
            frame_h, frame_w = frame.shape[:2]
            strip_h, strip_w = strip.shape[:2]
            if strip_w < frame_w:
                pad_width = frame_w - strip_w
                strip = cv2.copyMakeBorder(strip, 0, 0, 0, pad_width, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            combined = cv2.vconcat([frame, strip])
            cv2.imshow('Matches Display', combined)

            if cv2.waitKey(wait_per_frame_ms) & 0xFF == ord('q'):
                break
        self.clear_cache()
        # cv2.destroyAllWindows()
    
    def run(self):
        self.clear_cache()
        while True:
            # print('running loop in display process')
            cmd = self.queue.get()
            typ = cmd.get('type')
            # print(f"Received command: {typ}")
            if typ == 'load_matches':
                self.load_matches(cmd['file_contents'])
            elif typ == 'load_frames':
                self.load_frames(cmd['frames'])
            elif typ == 'clear':
                self.clear_cache()
            elif typ == 'show':
                self.show_display(cmd.get('top_n', 3), cmd.get('wait_ms', 600))
            elif typ == 'exit':
                break

    # Helper to push commands
    def send(self, cmd):
        self.queue.put(cmd)

    def submit_matches(self, file_contents):
        self.send({'type': 'load_matches', 'file_contents': file_contents})

    def submit_frames(self, frames):
        self.send({'type': 'load_frames', 'frames': frames})

    def clear(self):
        self.send({'type': 'clear'})

    def show(self, top_n=3, wait_ms=600):
        self.send({'type': 'show', 'top_n': top_n, 'wait_ms': wait_ms})

    def stop(self):
        self.send({'type': 'exit'})
        cv2.destroyAllWindows()

class DisplayManager:
    """
    High-level wrapper around DisplayProcess.
    Buffers frames and matches, commits them in batches, and plays back.
    """
    def __init__(self):
        self.proc = DisplayProcess()
        self.proc.start()
        self._frame_dict = {}
        self.fps = 30
        self._matches_json = None

    def append_frame(self, frame_idx, frame):
        """Add or update a single frame to the buffer."""
        self._frame_dict[frame_idx] = frame
        # print(f"Appended frame {frame_idx} to buffer. Total frames: {len(self._frame_dict)}")

    def commit_frames(self):
        """Send all buffered frames to the display process and clear buffer."""
        items = list(self._frame_dict.items())
        if items:
            self.proc.submit_frames(items)
            self._frame_dict.clear()

    def append_matches(self, matches_json_str):
        """Load .matches JSON for the current batch of frames."""
        self._matches_json = matches_json_str
        self.proc.submit_matches(matches_json_str)

    def clear(self):
        """Clear both local buffers and process caches."""
        self._frame_dict.clear()
        self._matches_json = None
        self.proc.clear()
    def set_fps(self, fps):
        """Set the frames per second for playback."""
        self.fps = fps
    def play(self, top_n=3, framerate=-1):
        """Commit any remaining frames/matches, then display them."""
        self.commit_frames()
        if framerate < 0:
            framerate = self.fps
        print(f"Playing back with framerate: {framerate} FPS")
        if self._matches_json is None:
            raise RuntimeError("No matches loaded. Call append_matches() first.")
        wait_ms = max(1, int(1000/framerate))
        self.proc.show(top_n=top_n, wait_ms=wait_ms)

    def stop(self):
        """Terminate the display process."""
        self.proc.stop()
        self.proc.join()

# End of display_process.py
