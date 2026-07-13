// ============================================================
// imagen.js
// Sección "Imagen": cámara en vivo, subida de archivo,
// configuración de calibración/canales y llamada al backend
// de análisis. Expone (en el scope global compartido):
//   capturedImageData, currentAnalysisId, currentMmPerPx,
//   currentPositions, originalPositions, currentOriginalFileName
// que son usadas por ajustes.js
// ============================================================

// --- Referencias DOM: panel de cámara / captura ---
const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const capturedImage = document.getElementById('capturedImage');
const toggleCameraBtn = document.getElementById('toggleCameraBtn');
const captureBtn = document.getElementById('captureBtn');
const analyzeBtn = document.getElementById('analyzeBtn');
const clearBtn = document.getElementById('clearBtn');
const loading = document.getElementById('loading');
const error = document.getElementById('error');
const success = document.getElementById('success');
const results = document.getElementById('results');
const resultsContent = document.getElementById('resultsContent');
const cameraError = document.getElementById('cameraError');

// --- Referencias DOM: cámara en pantalla completa ---
const enlargeCameraBtn = document.getElementById('enlargeCameraBtn');
const fullscreenVideo = document.getElementById('fullscreenVideo');
const cameraFullscreenOverlay = document.getElementById('cameraFullscreenOverlay');
const reduceCameraBtn = document.getElementById('reduceCameraBtn');
const fullscreenCaptureBtn = document.getElementById('fullscreenCaptureBtn');

// --- Estado de cámara / captura ---
let stream = null;
let isCameraActive = false;
let capturedImageData = null;

// --- Estado del análisis (compartido con ajustes.js) ---
let currentAnalysisId = null;
let currentMmPerPx = null;
let currentPositions = {};
let originalPositions = {};
let currentOriginalFileName = '';

// --- Configuración de calibración / canales ---
let configCalibrationMethod = 'camera_distance';  // 'camera_distance' | 'mark_size'
let configCameraDistanceMm = 100;
let configMarkSizeMm = 10;

// Inicializar cámara
async function initCamera() {
    try {
        cameraError.classList.remove('show');
        cameraError.textContent = '';

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('Tu navegador no soporta acceso a cámara');
        }

        stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'user'
            }
        });

        video.srcObject = stream;
        isCameraActive = true;
        toggleCameraBtn.textContent = 'Detener Cámara';
        toggleCameraBtn.classList.add('btn-danger');
        toggleCameraBtn.classList.remove('btn-secondary');
        captureBtn.disabled = false;
    } catch (err) {
        cameraError.classList.add('show');
        cameraError.textContent = `Error: ${err.message}. Verifica que hayas permitido acceso a la cámara.`;
        console.error('Error al acceder a la cámara:', err);
    }
}

// Detener cámara
function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
        isCameraActive = false;
    }
    video.srcObject = null;
    toggleCameraBtn.textContent = 'Iniciar Cámara';
    toggleCameraBtn.classList.remove('btn-danger');
    toggleCameraBtn.classList.add('btn-secondary');
    captureBtn.disabled = true;
}

// Toggle cámara
toggleCameraBtn.addEventListener('click', () => {
    if (isCameraActive) {
        stopCamera();
    } else {
        initCamera();
    }
});

// Capturar foto
captureBtn.addEventListener('click', () => {
    if (!isCameraActive || !video.srcObject) {
        error.classList.add('show');
        error.textContent = 'La cámara no está activa';
        return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);

    capturedImageData = canvas.toDataURL('image/jpeg', 0.95);
    capturedImage.src = capturedImageData;
    capturedImage.classList.add('show');
    analyzeBtn.disabled = false;
    clearBtn.disabled = false;

    error.classList.remove('show');
    success.classList.remove('show');
    results.style.display = 'none';

    // Analizar automáticamente después de capturar
    setTimeout(() => {
        analyzeImage();
    }, 500);
});

// Función para analizar imagen
async function analyzeImage() {
    if (!capturedImageData) {
        error.classList.add('show');
        error.textContent = 'No hay imagen capturada';
        return;
    }

    try {
        loading.style.display = 'block';
        error.classList.remove('show');
        success.classList.remove('show');
        results.style.display = 'none';

        // Convertir base64 a blob
        const res = await fetch(capturedImageData);
        const blob = await res.blob();

        // Crear FormData
        const formData = new FormData();
        formData.append('file', blob, 'capture.jpg');

        // Enviar al backend con el metodo de medicion, los valores del metodo de medicion y los canales elegidos
        const url = new URL('/api/v1/detection/analyze', window.location.origin);
        const method = document.querySelector('input[name="calMethod"]:checked').value;
        const channels = document.querySelectorAll('.ch-channel:checked');

        // cambio entre metodos + sus valores respectivos de tamano/distancia
        url.searchParams.append('calibration_method', method);
        if (method === 'camera_distance') {
            url.searchParams.append('camera_distance_mm', document.getElementById('cameraDistInput').value);
        } else {
            url.searchParams.append('mark_size_mm', document.getElementById('markSizeInputField').value);
        }

        // agrega los canales como elegidos
        channels.forEach(cb => url.searchParams.append('channels', cb.value));

        url.searchParams.append('save_outputs', 'true');

        const response = await fetch(url.toString(), {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error en el servidor');
        }

        const data = await response.json();
        displayResults(data);
        currentOriginalFileName = data.filename || 'capture.jpg';

        // Busca el id de la imagen analizada y inicializa las posiciones actuales y cambiadas a las posiciones incluidas en los canales de datos originales.
        currentAnalysisId = data.id;
        currentMmPerPx = data.mm_per_px;
        currentOriginalFileName = data.filename || '';
        originalPositions = {};
        currentPositions = {};
        ['C', 'M', 'Y', 'K'].forEach(ch => {
            if (data[ch]?.detected && data[ch]?.mark) {
                originalPositions[ch] = { x: data[ch].mark.x, y: data[ch].mark.y };
                currentPositions[ch] = { ...originalPositions[ch] };
            }
        });

        success.classList.add('show');
        success.textContent = '✓ Análisis completado exitosamente';
    } catch (err) {
        error.classList.add('show');
        error.textContent = `Error: ${err.message}`;
        console.error('Error:', err);
    } finally {
        loading.style.display = 'none';
    }
}

// Analizar imagen manualmente (botón)
analyzeBtn.addEventListener('click', () => {
    analyzeImage();
});

// Limpiar
clearBtn.addEventListener('click', () => {
    capturedImage.classList.remove('show');
    capturedImageData = null;
    analyzeBtn.disabled = true;
    clearBtn.disabled = true;
    error.classList.remove('show');
    success.classList.remove('show');
    results.style.display = 'none';
});

// Mostrar resultados
async function displayResults(data) {
    resultsContent.innerHTML = '';

    const resultsGallery = document.getElementById('resultsGallery');
    resultsGallery.innerHTML = '';

    // Cargar galería de imágenes guardadas, igual que en el historial
    if (data.id) {
        try {
            const res = await fetch(`/api/v1/detection/history/${data.id}/images`);
            if (res.ok) {
                const imgData = await res.json();
                imgData.filenames.forEach(filename => {
                    const img = document.createElement('img');
                    img.src = `/api/v1/detection/history/${data.id}/images/${filename}`;
                    img.alt = filename;
                    img.title = filename;
                    img.style.width = '100%';
                    img.style.borderRadius = '8px';
                    img.style.cursor = 'pointer';
                    img.onclick = () => openLightbox(img.src);
                    resultsGallery.appendChild(img);
                });
            }
        } catch (err) {
            console.error('Error cargando imágenes del análisis:', err);
        }
    }

    const channels = ['C', 'M', 'Y', 'K'];
    channels.forEach(channel => {
        const channelData = data[channel];
        if (channelData) {
            const div = document.createElement('div');
            div.className = `channel-result ${channelData.detected ? 'detected' : 'not-detected'}`;

            const status = channelData.detected ? 'Detectado ✓' : 'No detectado';
            const statusClass = channelData.detected ? 'detected' : 'not-detected';

            let html = `<div class="channel-name">
                Canal ${channel}
                <span class="status-badge ${statusClass}">${status}</span>
            </div>`;

            if (channelData.detected && channelData.mark) {
                html += `<div class="channel-details">
                    <div>Posición X: ${channelData.mark.x} px</div>
                    <div>Posición Y: ${channelData.mark.y} px</div>
                    <div>Confianza: ${(channelData.mark.score * 100).toFixed(2)}%</div>
                    <div>Escala: ${channelData.mark.scale}x</div>
                    <div>Píxeles: ${channelData.pixel_count}</div>
                </div>`;
            } else {
                html += `<div class="channel-details">
                    No se encontraron marcas en este canal
                </div>`;
            }

            div.innerHTML = html;
            resultsContent.appendChild(div);
        }
    });

    if (data.distances_to_k) {
        const distDiv = document.createElement('div');
        distDiv.className = 'channel-result';
        distDiv.style.borderLeftColor = '#4dabf7';

        let rows = '';
        ['C', 'M', 'Y'].forEach(ch => {
            const d = data.distances_to_k[ch];
            if (d && d.detected) {
                rows += `<tr>
                    <td>${ch}-K</td>
                    <td>${d.dx_mm.toFixed(3)}</td>
                    <td>${d.dy_mm.toFixed(3)}</td>
                    <td>${d.dist_mm.toFixed(3)}</td>
                    <td>${d.dist_px.toFixed(1)}</td>
                </tr>`;
            } else {
                rows += `<tr><td>${ch}</td><td colspan="4">No detectado</td></tr>`;
            }
        });

        distDiv.innerHTML = `
            <div class="channel-name">Distancias respecto a K</div>
            <table style="width:100%; border-collapse: collapse; font-size:13px; margin-top:8px;">
                <thead>
                    <tr>
                        <th style="text-align:left;">Canal</th>
                        <th style="text-align:left;">Δx (mm)</th>
                        <th style="text-align:left;">Δy (mm)</th>
                        <th style="text-align:left;">Dist (mm)</th>
                        <th style="text-align:left;">Dist (px)</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;
        resultsContent.appendChild(distDiv);
    }

    results.style.display = 'block';
}

// Auto-iniciar cámara al cargar la página
window.addEventListener('load', () => {
    // Opcional: descomentar para auto-iniciar
    // initCamera();
});

// Subir imagen
document.getElementById('uploadBtn').addEventListener('click', () => {
    document.getElementById('fileInput').click();
});

document.getElementById('fileInput').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    document.getElementById('fileName').textContent = file.name;

    const reader = new FileReader();
    reader.onload = function(e) {
        capturedImageData = e.target.result;
        capturedImage.src = capturedImageData;
        capturedImage.classList.add('show');
        analyzeBtn.disabled = false;
        clearBtn.disabled = false;

        error.classList.remove('show');
        success.classList.remove('show');
        results.style.display = 'none';

        // Analizar automáticamente
        setTimeout(() => analyzeImage(), 500);
    };
    reader.readAsDataURL(file);
});

// Para opciones de configuracion de imagenes.
document.querySelectorAll('input[name="calMethod"]').forEach(el => {
    el.addEventListener('change', () => {
        const isDist = document.querySelector('input[name="calMethod"]:checked').value === 'camera_distance';
        document.getElementById('distanceInput').style.display = isDist ? 'block' : 'none';
        document.getElementById('markSizeInput').style.display = isDist ? 'none' : 'block';
    });
});

// *** Controles para FullScreen de Camara

// Ampliar cámara
enlargeCameraBtn.addEventListener('click', () => {
    if (!stream) { error.textContent = 'La cámara no está activa'; error.classList.add('show'); return; }
    cameraFullscreenOverlay.style.display = 'flex';
    document.body.classList.add('fullscreen-active');
    fullscreenVideo.srcObject = stream;
});

// Reducir cámara
reduceCameraBtn.addEventListener('click', () => {
    cameraFullscreenOverlay.style.display = 'none';
    document.body.classList.remove('fullscreen-active');
    fullscreenVideo.srcObject = null;
});

// Capturar desde fullscreen (reusa misma lógica que captureBtn)
fullscreenCaptureBtn.addEventListener('click', () => {
    canvas.width = fullscreenVideo.videoWidth || video.videoWidth;
    canvas.height = fullscreenVideo.videoHeight || video.videoHeight;
    ctx.drawImage(fullscreenVideo, 0, 0);

    capturedImageData = canvas.toDataURL('image/jpeg', 0.95);
    capturedImage.src = capturedImageData;
    capturedImage.classList.add('show');
    analyzeBtn.disabled = false;
    clearBtn.disabled = false;

    // Cerrar fullscreen y analizar
    reduceCameraBtn.click();
    setTimeout(() => analyzeImage(), 500);
});

// Cerrar con tecla Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && cameraFullscreenOverlay.style.display === 'flex') {
        reduceCameraBtn.click();
    }
});
