document.addEventListener('DOMContentLoaded', function(){
    const mosaicForm = document.getElementById('mosaicForm');
    const tileSizeSlider = document.getElementById('tile_size');
    const tileSizeValue = document.getElementById('tile_size_value');
    const mainVisibilitySlider = document.getElementById('main_visibility');
    const mainVisibilityValue = document.getElementById('main_visibility_value');
    const finalScaleSlider = document.getElementById('final_scale');
    const finalScaleValue = document.getElementById('final_scale_value');
    const maxMosaicDefSlider = document.getElementById('max_mosaic_definition');
    const maxMosaicDefValue = document.getElementById('max_mosaic_definition_value');
    const minUsageSlider = document.getElementById('min_usage');
    const minUsageValue = document.getElementById('min_usage_value');
  
    const loadingDiv = document.getElementById('loader');
    const logMessagesDiv = document.getElementById('logMessages');
    const mosaicImage = document.getElementById('mosaicImage');
  
    const mosaicWrapper = document.getElementById('mosaic-wrapper');
    const zoomInBtn = document.getElementById('zoom_in');
    const zoomOutBtn = document.getElementById('zoom_out');
    const fullscreenBtn = document.getElementById('fullscreen_btn');
    const mosaicContainer = document.getElementById('mosaic-container');
  
    let currentZoom = 1.0;
    const MIN_ZOOM = 0.05;
  
    let debounceTimer;
    const DEBOUNCE_DELAY = 3000; // 3 secondes
  
    // Variables pour la simulation des logs
    let logTimer;
    const logMessages = [
      "Préparation des images...",
      "Calcul des couleurs moyennes...",
      "Assemblage des tuiles...",
      "Application des effets artistiques...",
      "Finalisation de la mosaïque..."
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
  
    // Mise à jour des valeurs affichées et déclenchement du debounce
    tileSizeSlider.addEventListener('input', () => {
      tileSizeValue.textContent = tileSizeSlider.value;
      debounceSubmit();
    });
    mainVisibilitySlider.addEventListener('input', () => {
      mainVisibilityValue.textContent = mainVisibilitySlider.value;
      debounceSubmit();
    });
    finalScaleSlider.addEventListener('input', () => {
      finalScaleValue.textContent = finalScaleSlider.value;
      debounceSubmit();
    });
    maxMosaicDefSlider.addEventListener('input', () => {
      maxMosaicDefValue.textContent = maxMosaicDefSlider.value;
      debounceSubmit();
    });
    minUsageSlider.addEventListener('input', () => {
      minUsageValue.textContent = minUsageSlider.value;
      debounceSubmit();
    });
  
    document.getElementById('main_image').addEventListener('change', () => {
      debounceSubmit(0);
    });
    document.getElementById('tile_images').addEventListener('change', () => {
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
      const formData = new FormData(mosaicForm);
      fetch('/generate', {
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
            mosaicImage.src = 'data:image/jpeg;base64,' + data.image;
          }
        })
        .catch(error => {
          loadingDiv.style.display = 'none';
          stopLogUpdates();
          alert("Erreur lors de la génération de la mosaïque.");
          console.error(error);
        });
    }
  
    function updateZoom() {
      mosaicWrapper.style.transform = `scale(${currentZoom})`;
    }
  
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
  
    mosaicImage.onload = function() {
      // On force l'échelle initiale à 1 pour que l'image remplisse tout le container
      currentZoom = 1;
      updateZoom();
      const resolutionDisplay = document.getElementById('mosaicResolution');
      resolutionDisplay.textContent = `${mosaicImage.naturalWidth} x ${mosaicImage.naturalHeight}`;
    };
  
    fullscreenBtn.addEventListener('click', () => {
      if (!document.fullscreenElement) {
        mosaicContainer.requestFullscreen().catch(err => {
          alert(`Erreur lors du passage en plein écran: ${err.message}`);
        });
      } else {
        document.exitFullscreen();
      }
    });
  
    // Lancement automatique si des fichiers sont déjà sélectionnés
    if (document.getElementById('main_image').files.length > 0 && document.getElementById('tile_images').files.length > 0) {
      submitForm();
    }
  });
  