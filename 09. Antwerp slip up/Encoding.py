import cv2
import numpy as np

def generate_and_inject(input_video):
    cap = cv2.VideoCapture(input_video)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    if height % 2 != 0:
        height -= 1

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    cam1_out = cv2.VideoWriter(
        'cam1.mp4',
        fourcc,
        fps,
        (width, height // 2)
    )

    cam2_out = cv2.VideoWriter(
        'cam2.mp4',
        fourcc,
        fps,
        (width, height // 2)
    )

    Y_even = np.arange(0, height, 2)
    Y_odd = np.arange(1, height, 2)

    frame_t = 0

    while cap.isOpened():
        ret, frame = cap.read()

        if not ret:
            break

        frame = frame[:height, :width]

        # The backward 10:42:09 encoding
        # DIVISOR = 9
        # DRIFT   = 42
        # MODULO  = 10

        shift_even = (
            (Y_even**2 // 9)
            + (42 * frame_t)
            + (Y_even % 10)
        )

        shift_odd = (
            (Y_odd**2 // 9)
            + (42 * frame_t)
            + (Y_odd % 10)
        )

        img_even = frame[0::2, :, :]
        img_odd = frame[1::2, :, :]

        # Cam 1 shifts right (-)
        col_idx_even = (
            np.arange(width)[None, :]
            - shift_even[:, None]
        ) % width

        scrambled_even = img_even[
            np.arange(height // 2)[:, None],
            col_idx_even
        ]

        # Cam 2 shifts left (+)
        col_idx_odd = (
            np.arange(width)[None, :]
            + shift_odd[:, None]
        ) % width

        scrambled_odd = img_odd[
            np.arange(height // 2)[:, None],
            col_idx_odd
        ]

        cam1_out.write(scrambled_even)
        cam2_out.write(scrambled_odd)

        frame_t += 1

    cap.release()
    cam1_out.release()
    cam2_out.release()
    # INJECT EOF FORENSICS HINTS
    cam1_payload = b"""
---SYSTEM DUMP---
WARNING: Anti-forensics daemon zeroed constants.
DIVISOR = [REDACTED]
DRIFT = [REDACTED]
MODULO = [REDACTED]
"""

    with open('cam1.mp4', 'ab') as f1:
        f1.write(cam1_payload)

    cam2_payload = b"""
---RECOVERED FRAGMENT---

Cam 1 shifts right (-), Cam 2 shifts left (+).

The shift is calculated as follows:

Take the row number, square it, and integer-divide the result by DIVISOR,
then add DRIFT multiplied by the frame number,
then add the remainder of the row number divided by MODULO.
"""

    with open('cam2.mp4', 'ab') as f2:
        f2.write(cam2_payload)

    print("[+] Challenge generated.")
    print("[+] EOF forensic hints injected into cam1.mp4 and cam2.mp4.")

generate_and_inject("input.mp4")
