// ============================================================
// ajustes.js
// Sección "Ajustes": vista de ajuste manual de posiciones de
// los registros CMYK sobre el canvas (zoom, pan, arrastre) y
// guardado de posiciones (recalcula distancias px -> mm).
// Usa variables definidas en imagen.js:
//   capturedImageData, currentAnalysisId, currentPositions,
//   originalPositions
// ============================================================

// --- Referencias DOM ---
const adjustView = document.getElementById('adjustView');
const adjustCanvas = document.getElementById('adjustCanvas');
const saveAdjustBtn = document.getElementById('saveAdjustBtn');
const cancelAdjustBtn = document.getElementById('cancelAdjustBtn');
const cancelAdjustBtn2 = document.getElementById('cancelAdjustBtn2');
const restoreOriginalBtn = document.getElementById('restoreOriginalBtn');

document.getElementById('adjustBtn').addEventListener('click', showAdjustView);

document.getElementById('hideOthersCheck').addEventListener('change', (e) => {
    hideOtherChannels = e.target.checked;
    redrawAdjustCanvas();
});

// --- Estado de la vista de ajuste ---
let hideOtherChannels = false;
let currentRoiMargin = 300;

let zoomLevel = 1.0;
let panOffsetX = 0;    // centro del viewport en coordenadas ROI (px)
let panOffsetY = 0;
let isPanning = false;
let panStartX = 0, panStartY = 0;
let panStartOffX = 0, panStartOffY = 0;

let dragChannel = null; // canal que se está arrastrando (reemplaza isDragging)
let dragOffsetX = 0, dragOffsetY = 0;
let roiOffsetX = 0, roiOffsetY = 0; // offset del ROI en imagen completa

let selectedChannel = 'C';
let currentMarkerRadius = 8;
let isDragging = false;

saveAdjustBtn.addEventListener('click', saveAdjustedPositions);

cancelAdjustBtn.addEventListener('click', () => {
    currentPositions = {};
    Object.keys(originalPositions).forEach(ch => {
        currentPositions[ch] = { ...originalPositions[ch] };
    });
    adjustView.style.display = 'none';
    mainView.style.display = 'block';
});

cancelAdjustBtn2.addEventListener('click', () => {
    currentPositions = {};
    Object.keys(originalPositions).forEach(ch => {
        currentPositions[ch] = { ...originalPositions[ch] };
    });
    adjustView.style.display = 'none';
    mainView.style.display = 'block';
});

restoreOriginalBtn.addEventListener('click', () => {
    currentPositions = {};
    Object.keys(originalPositions).forEach(ch => {
        currentPositions[ch] = { ...originalPositions[ch] };
    });
    redrawAdjustCanvas();
});

function showAdjustView() {
    updateZoomDisplay();
    updateChannelUI();

    // Ocultar mainView, mostrar adjustView
    mainView.style.display = 'none';
    adjustView.style.display = 'block';

    selectedChannel = 'C';
    document.querySelectorAll('.channel-btn').forEach(b =>
        b.classList.toggle('active', b.dataset.channel === selectedChannel)
    );

    const ctx = adjustCanvas.getContext('2d');

    // Cargar imagen original desde capturedImageData
    const img = new Image();
    img.onload = function() {
        // Calcular ROI alrededor de K
        const baseK = originalPositions['K'] || currentPositions['K'];
        const rx1 = Math.max(baseK.x - currentRoiMargin, 0);
        const ry1 = Math.max(baseK.y - currentRoiMargin, 0);
        const rx2 = Math.min(baseK.x + currentRoiMargin, img.width);
        const ry2 = Math.min(baseK.y + currentRoiMargin, img.height);

        roiOffsetX = rx1;
        roiOffsetY = ry1;

        adjustCanvas.width = rx2 - rx1;
        adjustCanvas.height = ry2 - ry1;

        panOffsetX = (adjustCanvas.width / 2) / zoomLevel;   // centro del ROI
        panOffsetY = (adjustCanvas.height / 2) / zoomLevel;

        ctx.clearRect(0, 0, adjustCanvas.width, adjustCanvas.height);

        // Dibujar ROI recortado
        ctx.drawImage(img, rx1, ry1, adjustCanvas.width, adjustCanvas.height, 0, 0, adjustCanvas.width, adjustCanvas.height);

        // Dibujar marcadores para cada canal
        drawAllMarkers(ctx, currentPositions, rx1, ry1);
    };
    img.src = capturedImageData;
}

// ============ DRAG ============

function redrawAdjustCanvas() {
    const ctx = adjustCanvas.getContext('2d');
    const img = new Image();
    img.onload = function() {
        const vw = adjustCanvas.width / zoomLevel;   // ancho del viewport en px de imagen
        const vh = adjustCanvas.height / zoomLevel;   // alto del viewport
        const srcX = roiOffsetX + panOffsetX - vw / 2;
        const srcY = roiOffsetY + panOffsetY - vh / 2;

        ctx.clearRect(0, 0, adjustCanvas.width, adjustCanvas.height);
        ctx.drawImage(img, srcX, srcY, vw, vh, 0, 0, adjustCanvas.width, adjustCanvas.height);
        drawAllMarkers(ctx);
    };
    img.src = capturedImageData;
}

function drawAllMarkers(ctx) {
    const colors = { 'C': 'cyan', 'M': 'magenta', 'Y': 'yellow', 'K': 'gray' };
    ['C', 'M', 'Y', 'K'].forEach(ch => {
        if (!currentPositions[ch]) return;
        if (hideOtherChannels && ch !== selectedChannel) return;
        const p = worldToScreen(currentPositions[ch].x, currentPositions[ch].y);
        // círculo
        ctx.beginPath(); ctx.arc(p.x, p.y, currentMarkerRadius, 0, 2 * Math.PI);
        ctx.fillStyle = colors[ch]; ctx.fill();
        ctx.strokeStyle = 'white'; ctx.lineWidth = 2; ctx.stroke();
        // crosshair
        ctx.beginPath(); ctx.moveTo(p.x - 15, p.y); ctx.lineTo(p.x + 15, p.y);
        ctx.moveTo(p.x, p.y - 15); ctx.lineTo(p.x, p.y + 15);
        ctx.strokeStyle = colors[ch]; ctx.lineWidth = 2; ctx.stroke();
        // label
        ctx.fillStyle = 'white'; ctx.font = 'bold 12px sans-serif';
        ctx.fillText(ch, p.x + 12, p.y - 12);
    });
}

function hitTestMarker(sx, sy) {
    const threshold = currentMarkerRadius + 10; // px en pantalla
    let best = null, bestDist = threshold;
    ['C', 'M', 'Y', 'K'].forEach(ch => {
        if (!currentPositions[ch]) return;
        const p = worldToScreen(currentPositions[ch].x, currentPositions[ch].y);
        const d = Math.hypot(sx - p.x, sy - p.y);
        if (d < bestDist) { bestDist = d; best = ch; }
    });
    return best;
}

// Screen (canvas pixel) → World (imagen global)
function screenToWorld(sx, sy) {
    return {
        x: (sx - adjustCanvas.width / 2) / zoomLevel + panOffsetX + roiOffsetX,
        y: (sy - adjustCanvas.height / 2) / zoomLevel + panOffsetY + roiOffsetY,
    };
}

// World → Screen
function worldToScreen(wx, wy) {
    return {
        x: (wx - roiOffsetX - panOffsetX) * zoomLevel + adjustCanvas.width / 2,
        y: (wy - roiOffsetY - panOffsetY) * zoomLevel + adjustCanvas.height / 2,
    };
}

function mouseToCanvas(e) {
    const rect = adjustCanvas.getBoundingClientRect();
    return {
        x: (e.clientX - rect.left) * (adjustCanvas.width / rect.width),
        y: (e.clientY - rect.top) * (adjustCanvas.height / rect.height),
    };
}

// Zoom centrado en cursor
function applyZoom(newZoom, cx, cy) {
    const world = screenToWorld(cx, cy);
    zoomLevel = Math.max(0.5, Math.min(20, newZoom));
    panOffsetX = world.x - roiOffsetX - (cx - adjustCanvas.width / 2) / zoomLevel;
    panOffsetY = world.y - roiOffsetY - (cy - adjustCanvas.height / 2) / zoomLevel;
    updateZoomDisplay();
    redrawAdjustCanvas();
}

function updateZoomDisplay() {
    document.getElementById('zoomLevelDisplay').textContent = zoomLevel.toFixed(1) + 'x';
}

function zoomIn() {
    const cx = adjustCanvas.width / 2;
    const cy = adjustCanvas.height / 2;
    applyZoom(zoomLevel * 1.3, cx, cy);
}

function zoomOut() {
    const cx = adjustCanvas.width / 2;
    const cy = adjustCanvas.height / 2;
    applyZoom(zoomLevel / 1.3, cx, cy);
}

function fitView() {
    zoomLevel = 1.0;
    panOffsetX = adjustCanvas.width / 2;
    panOffsetY = adjustCanvas.height / 2;
    updateZoomDisplay();
    redrawAdjustCanvas();
}

// Obtener canales disponibles para agregar
function getMissingChannels() {
    return ['C', 'M', 'Y'].filter(ch => !currentPositions[ch]);
}

// Agregar canal en el centro del ROI visible
function addChannel(ch) {
    if (currentPositions[ch]) return;
    const centerX = Math.round(roiOffsetX + adjustCanvas.width / 2) + 10;
    const centerY = Math.round(roiOffsetY + adjustCanvas.height / 2) + 10;
    currentPositions[ch] = { x: centerX, y: centerY };
    selectedChannel = ch;
    updateChannelUI();
    redrawAdjustCanvas();
}

// Eliminar canal (excepto K)
function removeChannel(ch) {
    if (ch === 'K') return;
    delete currentPositions[ch];
    if (selectedChannel === ch) {
        selectedChannel = Object.keys(currentPositions).find(c => c !== 'K') || 'K';
    }
    updateChannelUI();
    redrawAdjustCanvas();
}

// Actualizar estado visual de botones
function updateChannelUI() {
    document.querySelectorAll('.channel-btn').forEach(btn => {
        const ch = btn.dataset.channel;
        const exists = !!currentPositions[ch];
        btn.disabled = !exists && ch !== 'K'; // K siempre existe
        btn.classList.toggle('active', ch === selectedChannel && exists);
        btn.classList.toggle('disabled', !exists && ch !== 'K');
    });
    // Actualizar botón "−"
    document.getElementById('removeChannelBtn').disabled = selectedChannel === 'K';
    // Actualizar dropdown de agregar
    updateAddDropdown();
}

// Llenar dropdown con canales faltantes
function updateAddDropdown() {
    const dropdown = document.getElementById('addChannelDropdown');
    const missing = getMissingChannels();
    if (missing.length === 0) {
        dropdown.innerHTML = '<div style="padding: 8px; color: #999; font-size: 13px;">Todos los canales presentes</div>';
        return;
    }
    dropdown.innerHTML = missing.map(ch => {
        const name = { C: 'Cian', M: 'Magenta', Y: 'Amarillo' }[ch];
        const color = { C: 'cyan', M: 'magenta', Y: 'gold' }[ch];
        return `<div data-channel="${ch}" style="padding: 8px 12px; cursor: pointer; font-size: 13px; border-bottom: 1px solid #eee; color: #333;">
            <span style="color: ${color}; font-weight: 700;">${ch}</span> ${name}
        </div>`;
    }).join('');
    dropdown.querySelectorAll('[data-channel]').forEach(el => {
        el.addEventListener('click', () => {
            addChannel(el.dataset.channel);
            dropdown.style.display = 'none';
        });
    });
}

document.getElementById('addChannelBtn').addEventListener('click', (e) => {
    const dropdown = document.getElementById('addChannelDropdown');
    updateAddDropdown();
    dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
    e.stopPropagation();
});

// Cerrar dropdown al hacer clic fuera
document.addEventListener('click', () => {
    document.getElementById('addChannelDropdown').style.display = 'none';
});

document.getElementById('removeChannelBtn').addEventListener('click', () => {
    removeChannel(selectedChannel);
});

document.querySelectorAll('.channel-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.channel-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedChannel = btn.dataset.channel;
    });
});

document.getElementById('decreaseSizeBtn').addEventListener('click', () => {
    currentMarkerRadius = Math.max(2, currentMarkerRadius - 2);
    document.getElementById('markerSizeDisplay').textContent = currentMarkerRadius;
    redrawAdjustCanvas();
});

document.getElementById('increaseSizeBtn').addEventListener('click', () => {
    currentMarkerRadius = Math.min(30, currentMarkerRadius + 2);
    document.getElementById('markerSizeDisplay').textContent = currentMarkerRadius;
    redrawAdjustCanvas();
});

// control de zoom
document.getElementById('fitViewBtn').addEventListener('click', () => {
    zoomLevel = 1.0;
    panOffsetX = adjustCanvas.width / 2;
    panOffsetY = adjustCanvas.height / 2;
    updateZoomDisplay();
    redrawAdjustCanvas();
});

// controles de teclado
document.addEventListener('keydown', (e) => {
    if (adjustView.style.display !== 'block') return;
    if (e.key === '+' || e.key === '=') { zoomIn(); e.preventDefault(); }
    if (e.key === '-') { zoomOut(); e.preventDefault(); }
    if (e.key === '0') { fitView(); }
    if (e.key === 'ArrowUp')    { panOffsetY -= 10 / zoomLevel; redrawAdjustCanvas(); }
    if (e.key === 'ArrowDown')  { panOffsetY += 10 / zoomLevel; redrawAdjustCanvas(); }
    if (e.key === 'ArrowLeft')  { panOffsetX -= 10 / zoomLevel; redrawAdjustCanvas(); }
    if (e.key === 'ArrowRight') { panOffsetX += 10 / zoomLevel; redrawAdjustCanvas(); }
});

document.getElementById('zoomInBtn').addEventListener('click', () => {
    const cx = adjustCanvas.width / 2;
    const cy = adjustCanvas.height / 2;
    applyZoom(zoomLevel * 1.3, cx, cy);
});

document.getElementById('zoomOutBtn').addEventListener('click', () => {
    const cx = adjustCanvas.width / 2;
    const cy = adjustCanvas.height / 2;
    applyZoom(zoomLevel / 1.3, cx, cy);
});

// Mouse events
adjustCanvas.addEventListener('mousedown', (e) => {
    if (e.button === 2) { // click derecho → pan
        isPanning = true;
        panStartX = e.clientX;
        panStartY = e.clientY;
        panStartOffX = panOffsetX;
        panStartOffY = panOffsetY;
        adjustCanvas.style.cursor = 'grabbing';
        return;
    }
    // click izquierdo → detectar marcador o iniciar drag
    const pos = mouseToCanvas(e);
    const ch = hitTestMarker(pos.x, pos.y);
    if (ch) {
        isDragging = true;
        dragChannel = ch;
        selectedChannel = ch;
        // actualizar botón toggle
        document.querySelectorAll('.channel-btn').forEach(b =>
            b.classList.toggle('active', b.dataset.channel === ch)
        );
    }
});

adjustCanvas.addEventListener('mousemove', (e) => {
    const pos = mouseToCanvas(e);
    const rect = adjustCanvas.getBoundingClientRect();

    if (isPanning) {
        const scale = adjustCanvas.width / rect.width;
        const dx = (e.clientX - panStartX) * scale / zoomLevel;
        const dy = (e.clientY - panStartY) * scale / zoomLevel;
        panOffsetX = panStartOffX - dx;
        panOffsetY = panStartOffY - dy;
        redrawAdjustCanvas();
        return;
    }

    if (isDragging && dragChannel) {
        const world = screenToWorld(pos.x, pos.y);
        currentPositions[dragChannel] = { x: Math.round(world.x), y: Math.round(world.y) };
        redrawAdjustCanvas();
        return;
    }

    // hover cursor
    adjustCanvas.style.cursor = hitTestMarker(pos.x, pos.y) ? 'grab' : 'default';
});

adjustCanvas.addEventListener('mouseup', () => { isPanning = false; isDragging = false; dragChannel = null; });
adjustCanvas.addEventListener('mouseleave', () => { isPanning = false; isDragging = false; dragChannel = null; });
adjustCanvas.addEventListener('contextmenu', (e) => e.preventDefault());

// Touch events
adjustCanvas.addEventListener('touchstart', (e) => {
    e.preventDefault();
    isDragging = true;
    const touch = e.touches[0];
    const rect = adjustCanvas.getBoundingClientRect();
    const scaleX = adjustCanvas.width / rect.width;
    const scaleY = adjustCanvas.height / rect.height;
    const worldX = Math.round((touch.clientX - rect.left) * scaleX + roiOffsetX);
    const worldY = Math.round((touch.clientY - rect.top) * scaleY + roiOffsetY);
    currentPositions[selectedChannel] = { x: worldX, y: worldY };
    redrawAdjustCanvas();
});

adjustCanvas.addEventListener('touchmove', (e) => {
    e.preventDefault();
    if (!isDragging) return;
    const touch = e.touches[0];
    const rect = adjustCanvas.getBoundingClientRect();
    const scaleX = adjustCanvas.width / rect.width;
    const scaleY = adjustCanvas.height / rect.height;
    const worldX = Math.round((touch.clientX - rect.left) * scaleX + roiOffsetX);
    const worldY = Math.round((touch.clientY - rect.top) * scaleY + roiOffsetY);
    currentPositions[selectedChannel] = { x: worldX, y: worldY };
    redrawAdjustCanvas();
});

adjustCanvas.addEventListener('touchend', (e) => {
    e.preventDefault();
    isDragging = false;
});

async function saveAdjustedPositions() {
    try {
        loading.style.display = 'block';

        const response = await fetch(
            `/api/v1/detection/${currentAnalysisId}/adjust`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ positions: currentPositions })
            }
        );

        if (!response.ok) throw new Error('Error al ajustar posiciones');

        const data = await response.json();

        // Volver a la vista de resultados con datos actualizados
        adjustView.style.display = 'none';
        mainView.style.display = 'block';
        displayResults(data);

        success.classList.add('show');
        success.textContent = '✓ Posiciones ajustadas y distancias recalculadas';
    } catch (err) {
        error.classList.add('show');
        error.textContent = `Error: ${err.message}`;
    } finally {
        loading.style.display = 'none';
    }
}

// Debug: útil en desarrollo, se puede quitar en producción
console.log('Canvas size:', adjustCanvas.width, 'x', adjustCanvas.height);
console.log('CSS rect:', adjustCanvas.getBoundingClientRect());
console.log('Positions:', JSON.stringify(currentPositions));

adjustCanvas.addEventListener('mousemove', function test(e) {
    const pos = mouseToCanvas(e);
    const ch = hitTestMarker(pos.x, pos.y);
    console.log('Cursor at canvas px:', pos.x, pos.y, '→ hit:', ch);
    adjustCanvas.removeEventListener('mousemove', test);
}, { once: true });
