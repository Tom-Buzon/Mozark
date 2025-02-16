document.addEventListener('DOMContentLoaded', function(){
    // Éléments du formulaire et de l'affichage
    const paintingForm = document.getElementById('paintingForm');
    const numColorsSlider = document.getElementById('num_colors');
    const numColorsValue = document.getElementById('num_colors_value');
    const loadingDiv = document.getElementById('loader');
    const logMessagesDiv = document.getElementById('logMessages');
    const paintingImage = document.getElementById('paintingImage');
    const paletteContainer = document.getElementById('paletteContainer');
    const regenPaletteBtn = document.getElementById('regen_palette');
    const bwPreviewSmall = document.getElementById('bwPreviewSmall');
    
    // Éléments pour le zoom et le plein écran
    // Pour le zoom, nous appliquons la transformation sur le conteneur de visualisation (mosaic-wrapper)
    const mosaicWrapper = document.getElementById('mosaic-wrapper');
    // Pour le plein écran, nous souhaitons afficher l'ensemble du contenu, donc l'élément parent "main-content"
    const mainContent = document.getElementById('main-content');
    // Si vous ajoutez des boutons de zoom et fullscreen dans homemade_painting.html, récupérez-les ici (exemple ci-dessous)
    const zoomInBtn = document.getElementById('zoom_in'); 
    const zoomOutBtn = document.getElementById('zoom_out');
    const fullscreenBtn = document.getElementById('fullscreen_btn');
    const mosaicContainer = document.getElementById('mosaic-container');
    
    let debounceTimer;
    const DEBOUNCE_DELAY = 3000; // 3 secondes
    
    // Pour la simulation des logs
    let logTimer;
    const logMessages = [
      "Préparation de l'image...",
      "Quantification des couleurs...",
      "Extraction des contours...",
      "Création du rendu..."
    ];
    let logIndex = 0;
    
    function startLogUpdates() {
      logMessagesDiv.textContent = logMessages[logIndex];
      logTimer = setInterval(() => {
        logIndex = (logIndex + 1) % logMessages.length;
        logMessagesDiv.textContent = logMessages[logIndex];
      }, 1000);
    }
    
    function stopLogUpdates() {
      clearInterval(logTimer);
      logMessagesDiv.textContent = "";
    }
    
    // Déclenchement du debounce lors des modifications
    numColorsSlider.addEventListener('input', () => {
      numColorsValue.textContent = numColorsSlider.value;
      debounceSubmit();
    });
    
    document.getElementById('painting_image').addEventListener('change', () => {
      debounceSubmit(0);
    });
    
    function debounceSubmit(delay = DEBOUNCE_DELAY) {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        submitForm();
      }, delay);
    }
    
    function submitForm() {
      loadingDiv.style.display = 'flex';
      startLogUpdates();
      const formData = new FormData(paintingForm);
      // Récupérer la palette override depuis les inputs de couleur (s'ils existent)
      const paletteOverrideInputs = document.querySelectorAll('.palette-input');
      let paletteOverride = [];
      if (paletteOverrideInputs.length > 0) {
        paletteOverrideInputs.forEach(input => {
          paletteOverride.push(input.value);
        });
      }
      if (paletteOverride.length > 0) {
        formData.append('palette_override', paletteOverride.join(','));
      }
      fetch('/homemade_painting', {
        method: 'POST',
        body: formData
      })
        .then(response => response.json())
        .then(data => {
          loadingDiv.style.display = 'none';
          stopLogUpdates();
          if (data.error) {
            alert("Erreur : " + data.error);
          } else {
            paintingImage.src = 'data:image/jpeg;base64,' + data.image;
            // Afficher la palette dans le panneau de réglages
            displayPalette(data.palette);
            // Mettre à jour la prévisualisation BW dans le conteneur small
            if(data.bw_image) {
              bwPreviewSmall.src = 'data:image/jpeg;base64,' + data.bw_image;
            }
          }
        })
        .catch(error => {
          loadingDiv.style.display = 'none';
          stopLogUpdates();
          alert("Erreur lors de la génération de la peinture.");
          console.error(error);
        });
    }
    
    function displayPalette(palette) {
      paletteContainer.innerHTML = '<h3>Palette</h3>';
      palette.forEach(color => {
        const div = document.createElement('div');
        div.style.display = 'inline-block';
        div.style.margin = '0.5em';
        div.innerHTML = `<input type="color" class="palette-input" value="${color}">`;
        paletteContainer.appendChild(div);
      });
      document.querySelectorAll('.palette-input').forEach(input => {
        input.addEventListener('input', () => {
          debounceSubmit();
        });
      });
    }
    
    regenPaletteBtn.addEventListener('click', () => {
      const formData = new FormData();
      formData.append('num_colors', numColorsSlider.value);
      const paletteOverrideInputs = document.querySelectorAll('.palette-input');
      let currentPalette = [];
      if (paletteOverrideInputs.length > 0) {
        paletteOverrideInputs.forEach(input => {
          currentPalette.push(input.value);
        });
      }
      if (currentPalette.length > 0) {
        formData.append('base_palette', currentPalette.join(','));
      }
      fetch('/generate_palette', {
        method: 'POST',
        body: formData
      })
        .then(response => response.json())
        .then(data => {
          if (data.error) {
            alert("Erreur : " + data.error);
          } else {
            displayPalette(data.palette);
            debounceSubmit();
          }
        })
        .catch(error => {
          alert("Erreur lors de la génération de la nouvelle charte.");
          console.error(error);
        });
    });
    
    // Zoom functionality pour la visualisation
    let currentZoom = 1.0;
    const MIN_ZOOM = 0.05;
    
    function updateZoom() {
      mosaicWrapper.style.transform = `scale(${currentZoom})`;
    }
    
    // Si des boutons de zoom sont présents, ajouter des écouteurs
    if(zoomInBtn && zoomOutBtn) {
      zoomInBtn.addEventListener('click', () => {
        currentZoom += 0.03;
        updateZoom();
      });
      zoomOutBtn.addEventListener('click', () => {
        currentZoom = Math.max(MIN_ZOOM, currentZoom - 0.03);
        updateZoom();
      });
    
      mosaicWrapper.addEventListener('wheel', (e) => {
        e.preventDefault();
        if (e.deltaY < 0) {
          currentZoom += 0.03;
        } else {
          currentZoom = Math.max(MIN_ZOOM, currentZoom - 0.03);
        }
        updateZoom();
      });
    }
    
    // Plein écran pour l'ensemble du contenu
    if(fullscreenBtn && mosaicContainer) {
      fullscreenBtn.addEventListener('click', () => {
        if (!document.fullscreenElement) {
          mosaicContainer.requestFullscreen().catch(err => {
            alert(`Erreur lors du passage en plein écran: ${err.message}`);
          });
        } else {
          document.exitFullscreen();
        }
      });
    }
    
    // Lancement automatique si un fichier est déjà sélectionné
    if (document.getElementById('painting_image').files.length > 0) {
      submitForm();
    }
  });
  