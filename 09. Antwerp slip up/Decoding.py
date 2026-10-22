import cv2
import numpy as np

def solve_challenge():
    cap1 = cv2.VideoCapture('cam1.mp4')
    cap2 = cv2.VideoCapture('cam2.mp4')
    
    if not cap1.isOpened() or not cap2.isOpened():
        print("[-] Error: Could not open challenge videos.")
        return

    width = int(cap1.get(cv2.CAP_PROP_FRAME_WIDTH))
    half_height = int(cap1.get(cv2.CAP_PROP_FRAME_HEIGHT))
    height = half_height * 2
    fps = cap1.get(cv2.CAP_PROP_FPS) or 30.0
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('flag_recovered.mp4', fourcc, fps, (width, height))
    
    Y_even = np.arange(0, height, 2)
    Y_odd = np.arange(1, height, 2)
    
    frame_t = 0
    while True:
        ret1, frame_even = cap1.read()
        ret2, frame_odd = cap2.read()
        if not ret1 or not ret2: break
        
        shift_even = (Y_even**2 // 9) + (42 * frame_t) + (Y_even % 10)
        shift_odd = (Y_odd**2 // 9) + (42 * frame_t) + (Y_odd % 10)
        
        # Cam 1 shifted right (-), so we reverse by shifting left (+)
        un_even_cols = (np.arange(width)[None, :] + shift_even[:, None]) % width
        restored_even = frame_even[np.arange(half_height)[:, None], un_even_cols]
        
        # Cam 2 shifted left (+), so we reverse by shifting right (-)
        un_odd_cols = (np.arange(width)[None, :] - shift_odd[:, None]) % width
        restored_odd = frame_odd[np.arange(half_height)[:, None], un_odd_cols]
        
        full_frame = np.empty((height, width, 3), dtype=np.uint8)
        full_frame[0::2, :, :] = restored_even
        full_frame[1::2, :, :] = restored_odd
        
        out.write(full_frame)
        frame_t += 1
        
    cap1.release()
    cap2.release()
    out.release()
    print("[+] Vault video reconstructed.")

solve_challenge()
