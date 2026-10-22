#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
WORK="pkg"
rm -rf "$WORK" extractions && mkdir -p "$WORK"

# 1. Render the scene in Blender (only if render_raw.png doesn't exist yet), then run compose.py
if [ ! -f "render_raw.png" ]; then
    blender -b -P scene_render.py
fi
python3 compose.py

# 2. Subtle EXIF field ("Exclusive" = X in XOR)
exiftool -overwrite_original -ImageDescription="Planogram: v3 (Exclusive)" cam_base.jpg

# 3. Build the inner and outer archives inside pkg/
cat > "$WORK/notes.txt" <<'EOF'
Camera clock runs +11 minutes ahead. The mirror is convex and fitted opposite the back wall. The planogram diagram shows every slot in reading order: left to right, top to bottom. It's an exclusive display—two halves that cancel each other out. The ledger is keyed to the item that went missing.
EOF

cat > "$WORK/pos_ledger.csv" <<'EOF'
receipt_id,timestamp,event,sku,ref
R-0301,2026-03-14 09:12:40,SCAN,K3P6,
R-0588,2026-03-14 15:30:05,SCAN,Q8R2,
R-0592,2026-03-14 15:45:10,REFUND,Q8R2,R-0588
R-0701,2026-03-14 16:58:22,SCAN,Q8R2,
R-0703,2026-03-14 17:05:40,VOID,Q8R2,R-0701
R-0744,2026-03-14 17:15:02,SCAN,K3P6,
R-0766,2026-03-14 17:17:40,SCAN,Q8R2,
R-0770,2026-03-14 17:20:10,VOID,Q8R2,R-0766
R-0771,2026-03-14 17:20:30,SCAN,Q8R2,
EOF

(cd "$WORK" && zip -q -e -P Q8R2 ledger.zip pos_ledger.csv && rm -f pos_ledger.csv)
(cd "$WORK" && zip -q outer.zip planogram_v3.png notes.txt ledger.zip)
cp "$WORK/outer.zip" ./outer.zip

# 4. Concatenate Redacted JPEG + XOR PNG Mask + Outer ZIP into cam_frame_0730.jpg
cat cam_base.jpg shelf_mask.png outer.zip > cam_frame_0730.jpg

# 5. Verify pipeline
echo "--- exiftool ---"
exiftool cam_frame_0730.jpg | grep -i "Planogram"
echo "--- binwalk ---"
binwalk cam_frame_0730.jpg
echo "--- ledger password ---"
unzip -l -P Q8R2 "$WORK/ledger.zip" >/dev/null && echo "ledger.zip opens with Q8R2"

echo "Built cam_frame_0730.jpg successfully!"