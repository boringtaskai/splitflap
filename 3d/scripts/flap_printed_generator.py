import os
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ==========================================
# KONFIGURASI FINAL (Huruf Besar & Posisi Naik)
# ==========================================
CONFIG = {
    'DPI': 300,
    
    # --- GEOMETRI (TETAP) ---
    'MM_BODY_WIDTH': 50.0,
    'MM_NOTCH_NECK_WIDTH': 44.0,
    'MM_PIN_TOTAL_WIDTH': 54.0,
    'MM_HEIGHT_HALF': 42.8,
    'MM_PIN_HEIGHT': 2.8,
    'MM_NOTCH_HEIGHT': 8.0,
    'MM_CORNER_RADIUS': 3.0,
    
    # --- PENGATURAN POSISI HURUF (KUNCI PERBAIKAN) ---
    
    # 1. PENGANGKATAN TEKS (VERTICAL LIFT)
    # Semakin besar angka NEGATIF (-), huruf semakin NAIK ke atas menjauhi dasar.
    # Sebelumnya -4.0, sekarang saya ubah jadi -12.0 agar benar-benar naik.
    # Jika masih kurang naik, ubah jadi -15.0. Jika terlalu naik, ubah jadi -8.0.
    'TEXT_Y_SHIFT_MM': -12.0, 
    
    # 2. PADDING
    # Jarak aman kiri-kanan agar huruf besar tidak menabrak pinggir
    'TEXT_PADDING_MM': 3.0, 
    
    # --- WARNA ---
    'BG_COLOR': (20, 20, 20),
    'TEXT_COLOR': (255, 255, 255),
    'GUIDE_COLOR': (0, 255, 255),
    'ROTATE_TOP_HALF': True,
    
    'FONT_PATH': "arial.ttf", 
    'CHAR_SEQUENCE': "ABCDEFGHIJKLMNOPQRSTUVWXY012345678",
    'OUTPUT_DIR': "output_lifted_center"
}

def mm_to_px(mm):
    return int((mm / 25.4) * CONFIG['DPI'])

def create_complex_flap_shape(w_canvas, h_canvas):
    """Membentuk Geometri Pin & Notch (Tidak Berubah)."""
    body_w = mm_to_px(CONFIG['MM_BODY_WIDTH'])
    neck_w = mm_to_px(CONFIG['MM_NOTCH_NECK_WIDTH'])
    pin_w  = mm_to_px(CONFIG['MM_PIN_TOTAL_WIDTH'])
    h_pin = mm_to_px(CONFIG['MM_PIN_HEIGHT'])
    h_notch = mm_to_px(CONFIG['MM_NOTCH_HEIGHT'])
    radius = mm_to_px(CONFIG['MM_CORNER_RADIUS'])
    
    cx, cy = w_canvas // 2, h_canvas // 2
    body_l, body_r = cx - body_w//2, cx + body_w//2
    neck_l, neck_r = cx - neck_w//2, cx + neck_w//2
    pin_l, pin_r   = cx - pin_w//2, cx + pin_w//2
    pin_t, pin_b = cy - h_pin//2, cy + h_pin//2
    notch_t, notch_b = cy - h_notch, cy + h_notch
    
    mask = Image.new('L', (w_canvas, h_canvas), 0)
    draw = ImageDraw.Draw(mask)
    
    points = [
        (body_l, radius), (body_r, radius),
        (body_r, notch_t), (neck_r, notch_t),
        (neck_r, pin_t), (pin_r, pin_t),
        (pin_r, pin_b), (neck_r, pin_b),
        (neck_r, notch_b), (body_r, notch_b),
        (body_r, h_canvas - radius),
        (body_l, h_canvas - radius),
        (body_l, notch_b), (neck_l, notch_b),
        (neck_l, pin_b), (pin_l, pin_b),
        (pin_l, pin_t), (neck_l, pin_t),
        (neck_l, notch_t), (body_l, notch_t),
        (body_l, radius)
    ]
    draw.polygon(points, fill=255)
    
    # Rounded corners
    draw.pieslice((body_l, 0, body_l + 2*radius, 2*radius), 180, 270, fill=255)
    draw.rectangle((body_l + radius, 0, body_r - radius, radius), fill=255)
    draw.pieslice((body_r - 2*radius, 0, body_r, 2*radius), 270, 360, fill=255)
    draw.pieslice((body_l, h_canvas - 2*radius, body_l + 2*radius, h_canvas), 90, 180, fill=255)
    draw.rectangle((body_l + radius, h_canvas - radius, body_r - radius, h_canvas), fill=255)
    draw.pieslice((body_r - 2*radius, h_canvas - 2*radius, body_r, h_canvas), 0, 90, fill=255)
    
    return mask, points

def get_optimized_font(font_path, text, max_w, max_h):
    """Mencari font terbesar yang muat."""
    fontsize = 50
    font = ImageFont.truetype(font_path, fontsize)
    while True:
        left, top, right, bottom = font.getbbox(text)
        w = right - left
        h = bottom - top
        if w >= max_w or h >= max_h:
            fontsize -= 5 # Mundur sedikit agar aman
            return ImageFont.truetype(font_path, fontsize)
        fontsize += 5
        font = ImageFont.truetype(font_path, fontsize)

def draw_blueprints(draw, points):
    draw.line(points + [points[0]], fill=CONFIG['GUIDE_COLOR'], width=3)

def main():
    if not os.path.exists(CONFIG['OUTPUT_DIR']):
        os.makedirs(CONFIG['OUTPUT_DIR'])
        
    max_w_mm = max(CONFIG['MM_BODY_WIDTH'], CONFIG['MM_PIN_TOTAL_WIDTH'])
    w_px = mm_to_px(max_w_mm)
    h_half_px = mm_to_px(CONFIG['MM_HEIGHT_HALF'])
    h_total_px = h_half_px * 2
    
    # Area aman teks
    safe_w_px = mm_to_px(CONFIG['MM_BODY_WIDTH'] - (CONFIG['TEXT_PADDING_MM'] * 2))
    # Tinggi kita batasi agak longgar karena kita akan geser manual
    safe_h_px = h_total_px - mm_to_px(5) 
    
    print("⚙️  Menghitung ukuran font & menerapkan Vertical Lift...")
    
    # Cari font optimal
    font = get_optimized_font(CONFIG['FONT_PATH'], "8", safe_w_px, safe_h_px)
    
    shift_px = mm_to_px(CONFIG['TEXT_Y_SHIFT_MM'])
    shape_mask, poly_points = create_complex_flap_shape(w_px, h_total_px)
    chars = list(CONFIG['CHAR_SEQUENCE'])
    
    print(f"✅ Font Size: {font.size}")
    print(f"✅ Vertical Shift: {CONFIG['TEXT_Y_SHIFT_MM']} mm (Ke Atas)")
    
    for i in range(len(chars)):
        curr_char = chars[i]
        next_char = chars[(i + 1) % len(chars)]
        
        canvas_curr = Image.new('RGBA', (w_px, h_total_px), CONFIG['BG_COLOR'])
        canvas_next = Image.new('RGBA', (w_px, h_total_px), CONFIG['BG_COLOR'])
        d_curr = ImageDraw.Draw(canvas_curr)
        d_next = ImageDraw.Draw(canvas_next)
        
        def draw_lifted(d, char):
            left, top, right, bottom = font.getbbox(char)
            text_w = right - left
            text_h = bottom - top
            
            # Center Horizontal
            x = (w_px - text_w) / 2 - left
            
            # Center Vertical AWAL (Secara Matematis)
            y_center = (h_total_px - text_h) / 2
            
            # TERAPKAN LIFT (GESER NAIK)
            # shift_px bernilai negatif, jadi y akan berkurang (naik ke atas)
            y = y_center - top + shift_px
            
            d.text((x, y), char, font=font, fill=CONFIG['TEXT_COLOR'])
            
        draw_lifted(d_curr, curr_char)
        draw_lifted(d_next, next_char)
        
        # Cutting
        top_part = canvas_curr.crop((0, h_half_px, w_px, h_total_px))
        bottom_part = canvas_next.crop((0, 0, w_px, h_half_px))
        
        if CONFIG['ROTATE_TOP_HALF']:
            top_part = top_part.transpose(Image.ROTATE_180)
            
        final_img = Image.new('RGBA', (w_px, h_total_px), (0,0,0,0))
        final_img.paste(top_part, (0, 0))
        final_img.paste(bottom_part, (0, h_half_px))
        
        final_img.putalpha(shape_mask)
        d_final = ImageDraw.Draw(final_img)
        draw_blueprints(d_final, poly_points)
        
        filename = f"{i:03d}_{curr_char}_to_{next_char}.png"
        final_img.save(os.path.join(CONFIG['OUTPUT_DIR'], filename))
        print(f"✅ Generated: {filename}")

    print("\n🎉 Selesai! Huruf sudah dinaikkan (Lifted) menjauhi dasar kartu.")

if __name__ == "__main__":
    main()