# app.py
import io
import math
import base64
import numpy as np
from PIL import Image, ImageEnhance
from flask import Flask, render_template, request, jsonify

# Désactiver la limite de pixels pour éviter l'erreur de "decompression bomb"
Image.MAX_IMAGE_PIXELS = None

app = Flask(__name__)

# --- Fonctions de traitement image ---

def limit_image_definition(image, max_def):
    """Redimensionne l'image si sa largeur ou hauteur dépasse max_def, en conservant le ratio."""
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
    """
    Charge les images de tuiles depuis les fichiers uploadés, en les limitant à max_mosaic_def,
    puis en les redimensionnant à la taille de tuile souhaitée.
    Chaque tuile reçoit un compteur 'usage' initialisé à 0.
    """
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
    """
    Crée la mosaïque de manière séquentielle.
    Pour chaque bloc de l'image principale, on choisit la tuile dont la couleur moyenne est la plus proche.
    Pour favoriser l'utilisation des tuiles non encore utilisées, on applique un bonus sur la distance
    calculée en fonction de min_usage.
    """
    mosaic_width = (main_image.width // tile_size) * tile_size
    mosaic_height = (main_image.height // tile_size) * tile_size
    mosaic_image = Image.new('RGB', (mosaic_width, mosaic_height))
    
    bonus = (min_usage / 100.0) * 0.3  # ex: pour 100% → bonus = 0.3, pour 90% → bonus = 0.27
    
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

# --- Routes Flask ---

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
        
        # Récupération des paramètres
        tile_size = int(request.form.get('tile_size', 150))
        main_visibility = float(request.form.get('main_visibility', 0.2))
        final_scale = float(request.form.get('final_scale', 0.5))
        min_usage = float(request.form.get('min_usage', 90))  # % d'utilisation minimale
        max_mosaic_def = int(request.form.get('max_mosaic_definition', 1024))
        
        if not main_file or len(tile_files) == 0:
            return jsonify({'error': 'Images manquantes'}), 400
        
        # Traitement de l'image principale
        main_image = Image.open(main_file.stream).convert('RGB')
        upscale_factor = 15  # pour obtenir des détails fins
        main_image = upscale_image(main_image, upscale_factor)
        
        # Chargement des tuiles
        tiles = load_tiles_from_files(tile_files, tile_size, max_mosaic_def)
        if len(tiles) == 0:
            return jsonify({'error': 'Aucune image de tuile valide'}), 400
        
        # Création de la mosaïque
        mosaic = create_mosaic(main_image, tiles, tile_size, min_usage)
        
        # Limiter la résolution finale de la mosaïque
        mosaic = limit_image_definition(mosaic, max_mosaic_def)
        
        # Blend avec l'image principale
        if main_visibility > 0:
            main_resized = main_image.resize(mosaic.size, Image.LANCZOS)
            mosaic = Image.blend(mosaic, main_resized, main_visibility)
        
        # Redimensionnement final (scale)
        if final_scale != 1.0:
            final_size = (int(mosaic.width * final_scale), int(mosaic.height * final_scale))
            mosaic = mosaic.resize(final_size, Image.LANCZOS)
        
        # Encodage en base64
        img_io = io.BytesIO()
        mosaic.save(img_io, 'JPEG', quality=95)
        img_io.seek(0)
        base64_img = base64.b64encode(img_io.getvalue()).decode('utf-8')
        return jsonify({'image': base64_img})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
