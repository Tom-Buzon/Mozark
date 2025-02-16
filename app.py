# app.py
import io
import math
import base64
import random, colorsys
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from flask import Flask, render_template, request, jsonify

# Désactiver la limite de pixels pour éviter l'erreur de "decompression bomb"
Image.MAX_IMAGE_PIXELS = None

app = Flask(__name__)

# --- Fonctions de traitement image pour Mosaic (inchangées) ---

def limit_image_definition(image, max_def):
    if image.width > max_def or image.height > max_def:
        ratio = min(max_def / image.width, max_def / image.height)
        new_size = (int(image.width * ratio), int(image.height * ratio))
        return image.resize(new_size, Image.LANCZOS)
    return image

def upscale_image(image, scale_factor):
    new_size = (int(image.width * scale_factor), int(image.height * scale_factor))
    return image.resize(new_size, Image.LANCZOS)

def calculate_color_stats(image):
    img_array = np.array(image)
    avg_color = img_array.mean(axis=(0, 1))
    return avg_color, img_array.std(axis=(0, 1))

def load_tiles_from_files(files, tile_size, max_mosaic_def):
    tiles = []
    for f in files:
        try:
            img = Image.open(f.stream).convert('RGB')
            img = limit_image_definition(img, max_mosaic_def)
            img = img.resize((tile_size, tile_size), Image.LANCZOS)
            avg_color, _ = calculate_color_stats(img)
            tile = {"image": img, "avg_color": avg_color, "usage": 0}
            tiles.append(tile)
        except Exception as e:
            print(f"Erreur lors du chargement d'une tuile: {e}")
    return tiles

def create_mosaic(main_image, tiles, tile_size, min_usage):
    mosaic_width = (main_image.width // tile_size) * tile_size
    mosaic_height = (main_image.height // tile_size) * tile_size
    mosaic_image = Image.new('RGB', (mosaic_width, mosaic_height))
    
    bonus = (min_usage / 100.0) * 0.3
    for y in range(0, mosaic_height, tile_size):
        for x in range(0, mosaic_width, tile_size):
            block = main_image.crop((x, y, x + tile_size, y + tile_size))
            block_avg, _ = calculate_color_stats(block)
            best_tile = None
            best_eff_distance = float('inf')
            for tile in tiles:
                distance = np.linalg.norm(tile["avg_color"] - block_avg)
                effective_distance = distance * (1 - bonus) if tile["usage"] == 0 else distance
                if effective_distance < best_eff_distance:
                    best_eff_distance = effective_distance
                    best_tile = tile
            best_tile["usage"] += 1
            mosaic_image.paste(best_tile["image"], (x, y))
    return mosaic_image

# --- Traitement pour Homemade Painting ---

@app.route('/homemade_painting', methods=['GET', 'POST'])
def homemade_painting():
    if request.method == 'GET':
        return render_template('homemade_painting.html')
    try:
        painting_file = request.files.get('painting_image')
        num_colors = int(request.form.get('num_colors', 6))
        palette_override = request.form.get('palette_override', None)
        if not painting_file:
            return jsonify({'error': 'Image manquante'}), 400

        image = Image.open(painting_file.stream).convert('RGB')
        # Quantifier en mode "P" pour extraire la palette
        p_image = image.convert("P", palette=Image.ADAPTIVE, colors=num_colors)
        palette_data = p_image.getpalette()[:num_colors*3]
        colors = []
        for i in range(0, len(palette_data), 3):
            r, g, b = palette_data[i], palette_data[i+1], palette_data[i+2]
            hex_color = '#{:02x}{:02x}{:02x}'.format(r, g, b)
            colors.append(hex_color)
        if palette_override:
            new_palette = [c.strip() for c in palette_override.split(',')]
            palette_ints = []
            for hex_color in new_palette:
                if hex_color.startswith('#'):
                    hex_color = hex_color[1:]
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                palette_ints.extend([r, g, b])
            palette_ints += [0]*(768 - len(palette_ints))
            p_image.putpalette(palette_ints)
            colors = new_palette[:num_colors]
        quantized = p_image.convert("RGB")
        
        # Extraction des contours
        edges = quantized.filter(ImageFilter.FIND_EDGES)
        edges_gray = edges.convert("L")
        threshold_value = 50
        mask = edges_gray.point(lambda p: 255 if p > threshold_value else 0)
        black_img = Image.new("RGB", quantized.size, (0, 0, 0))
        # Ici, le composite force les zones de masque à devenir noires (pour avoir des lignes fines)
        result = Image.composite(black_img, quantized, mask)
        
        # Pour prévisualisation BW, créer une version inversée des bords (noir sur blanc)
        bw = ImageOps.invert(mask).convert("RGB")
        
        img_io = io.BytesIO()
        result.save(img_io, 'JPEG', quality=95)
        img_io.seek(0)
        base64_img = base64.b64encode(img_io.getvalue()).decode('utf-8')
        
        bw_io = io.BytesIO()
        bw.save(bw_io, 'JPEG', quality=95)
        bw_io.seek(0)
        base64_bw = base64.b64encode(bw_io.getvalue()).decode('utf-8')
        
        return jsonify({'image': base64_img, 'palette': colors, 'bw_image': base64_bw})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Génération d'une nouvelle palette ---
def generate_palette(num_colors, base_palette=None):
    # Si une palette de base est fournie, en utiliser la première couleur
    if base_palette:
        first_color = base_palette.split(',')[0]
        r = int(first_color[1:3], 16) / 255.0
        g = int(first_color[3:5], 16) / 255.0
        b = int(first_color[5:7], 16) / 255.0
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
    else:
        h = random.random()
        s = 0.6 + random.random() * 0.4
        v = 0.6 + random.random() * 0.4
    palette = []
    for i in range(num_colors):
        # Ajouter un léger décalage aléatoire pour varier à chaque appel
        new_h = (h + i / num_colors + random.uniform(-0.05, 0.05)) % 1.0
        r, g, b = colorsys.hsv_to_rgb(new_h, s, v)
        hex_color = '#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255))
        palette.append(hex_color)
    return palette

@app.route('/generate_palette', methods=['POST'])
def generate_palette_route():
    try:
        num_colors = int(request.form.get('num_colors', 6))
        base_palette = request.form.get('base_palette', None)
        new_palette = generate_palette(num_colors, base_palette)
        return jsonify({'palette': new_palette})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Routes existantes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/collection')
def collection():
    return render_template('collection.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        main_file = request.files.get('main_image')
        tile_files = request.files.getlist('tile_images')
        
        tile_size = int(request.form.get('tile_size', 150))
        main_visibility = float(request.form.get('main_visibility', 0.2))
        final_scale = float(request.form.get('final_scale', 0.5))
        min_usage = float(request.form.get('min_usage', 90))
        max_mosaic_def = int(request.form.get('max_mosaic_definition', 1024))
        
        if not main_file or len(tile_files) == 0:
            return jsonify({'error': 'Images manquantes'}), 400
        
        main_image = Image.open(main_file.stream).convert('RGB')
        upscale_factor = 15
        main_image = upscale_image(main_image, upscale_factor)
        
        tiles = load_tiles_from_files(tile_files, tile_size, max_mosaic_def)
        if len(tiles) == 0:
            return jsonify({'error': 'Aucune image de tuile valide'}), 400
        
        mosaic = create_mosaic(main_image, tiles, tile_size, min_usage)
        mosaic = limit_image_definition(mosaic, max_mosaic_def)
        if main_visibility > 0:
            main_resized = main_image.resize(mosaic.size, Image.LANCZOS)
            mosaic = Image.blend(mosaic, main_resized, main_visibility)
        if final_scale != 1.0:
            final_size = (int(mosaic.width * final_scale), int(mosaic.height * final_scale))
            mosaic = mosaic.resize(final_size, Image.LANCZOS)
        
        img_io = io.BytesIO()
        mosaic.save(img_io, 'JPEG', quality=95)
        img_io.seek(0)
        base64_img = base64.b64encode(img_io.getvalue()).decode('utf-8')
        return jsonify({'image': base64_img})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
