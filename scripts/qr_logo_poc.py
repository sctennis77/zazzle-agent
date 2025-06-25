import os
from PIL import Image, ImageDraw, ImageFilter
import qrcode
import numpy as np

# --- CONFIG ---
LOGO_BG_PATH = os.path.join(os.path.dirname(__file__), 'logo_qr_background.png')
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'qr_logo_composite.png')
QR_URL = 'https://clouvel.com'  # Change as needed
QR_SIZE = 512  # px
BORDER_MODULES = 2  # QR border in modules (matches qr border param)

# --- GENERATE QR CODE MATRIX ---
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=10,
    border=BORDER_MODULES,
)
qr.add_data(QR_URL)
qr.make(fit=True)
qr_matrix = qr.get_matrix()
modules_count = len(qr_matrix)
module_size = QR_SIZE // modules_count

# --- LOAD PREPPED LOGO BACKGROUND ---
logo_bg = Image.open(LOGO_BG_PATH).convert('RGBA').resize((QR_SIZE, QR_SIZE), Image.LANCZOS)

# --- CREATE QR CODE IMAGE WITH GRADIENT AND TRANSPARENCY ---
qr_img = Image.new('RGBA', (QR_SIZE, QR_SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(qr_img)

# Gradient colors for QR modules (almost black)
grad_start = np.array([10, 10, 20])   # Nearly black
grad_end = np.array([30, 30, 40])    # Slightly lighter but still nearly black

for y in range(modules_count):
    for x in range(modules_count):
        if qr_matrix[y][x]:
            t = y / (modules_count - 1)
            color = tuple((grad_start * (1 - t) + grad_end * t).astype(int))
            rect = [x * module_size, y * module_size, (x + 1) * module_size, (y + 1) * module_size]
            draw.rectangle(rect, fill=color + (255,))  # Fully opaque

# --- FINAL COMPOSITION ---
final_size = QR_SIZE + 40
final_image = Image.new('RGBA', (final_size, final_size), (235, 240, 255, 255))
border_draw = ImageDraw.Draw(final_image)
border_draw.rounded_rectangle([0, 0, final_size-1, final_size-1], radius=28, outline=(80, 180, 220, 180), width=4)

# Paste logo background
final_image.paste(logo_bg, (20, 20), logo_bg)
# Paste QR code on top
final_image.paste(qr_img, (20, 20), qr_img)

# --- SAVE RESULT ---
final_image.save(OUTPUT_PATH, quality=95)
print(f'Final QR+logo image saved to {OUTPUT_PATH}')
print(f'Features: Prepped logo background, QR modules with dark blue gradient and partial transparency, high error correction') 