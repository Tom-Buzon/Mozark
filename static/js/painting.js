document.addEventListener('DOMContentLoaded', function(){
    const paintingForm = document.getElementById('paintingForm');
    const numColorsSlider = document.getElementById('num_colors');
    const numColorsValue = document.getElementById('num_colors_value');
    const loadingDiv = document.getElementById('loader');
    const logMessagesDiv = document.getElementById('logMessages');
    const paintingImage = document.getElementById('paintingImage');
    const mosaicContainer = document.getElementById('mosaic-container');
    const paletteContainer = document.getElementById('paletteContainer');
    const regenPaletteBtn = document.getElementById('regen_palette');
    const bwPreviewSmall = document.getElementById('bwPreviewSmall');
  
    let debounceTimer;
    const DEBOUNCE_DELAY = 3000;
  
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
            // Afficher la palette
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
  
    if (document.getElementById('painting_image').files.length > 0) {
      submitForm();
    }
  });
  