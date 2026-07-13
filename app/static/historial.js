// ============================================================
// historial.js
// Sección "Historial": listado de análisis pasados, detalle de
// un registro, y el lightbox compartido para ampliar imágenes
// (usado tanto aquí como en imagen.js -> displayResults)
// ============================================================

// --- Referencias DOM ---
const mainView = document.getElementById('mainView');
const historyView = document.getElementById('historyView');
const viewHistoryBtn = document.getElementById('viewHistoryBtn');
const backToMainBtn = document.getElementById('backToMainBtn');
const backToListBtn = document.getElementById('backToListBtn');
const historyLoading = document.getElementById('historyLoading');
const historyError = document.getElementById('historyError');
const historyList = document.getElementById('historyList');
const historyDetail = document.getElementById('historyDetail');
const historyDetailImage = document.getElementById('historyDetailImage');
const historyDetailContent = document.getElementById('historyDetailContent');

viewHistoryBtn.addEventListener('click', () => {
    mainView.style.display = 'none';
    historyView.style.display = 'block';
    loadHistory();
});

backToMainBtn.addEventListener('click', () => {
    historyView.style.display = 'none';
    mainView.style.display = 'block';
});

backToListBtn.addEventListener('click', () => {
    historyDetail.style.display = 'none';
    historyList.style.display = 'block';
});

async function loadHistory() {
    historyError.classList.remove('show');
    historyList.innerHTML = '';
    historyDetail.style.display = 'none';
    historyList.style.display = 'block';
    historyLoading.style.display = 'block';

    try {
        const response = await fetch('/api/v1/detection/history');
        if (!response.ok) throw new Error('No se pudo cargar el historial');
        const records = await response.json();

        if (records.length === 0) {
            historyList.innerHTML = '<p style="color: #666;">Aún no hay análisis guardados.</p>';
            return;
        }

        records.forEach(record => {
            const item = document.createElement('div');
            item.className = 'channel-result';
            item.style.cursor = 'pointer';

            const date = new Date(record.timestamp).toLocaleString('es-DO');
            const colorCount = record.colors.length;

            item.innerHTML = `
                <div class="channel-name">${record.image_filename}</div>
                <div class="channel-details">
                    <div>Fecha: ${date}</div>
                    <div>Canales detectados: ${colorCount}</div>
                </div>
            `;

            item.addEventListener('click', () => showHistoryDetail(record));
            historyList.appendChild(item);
        });
    } catch (err) {
        historyError.classList.add('show');
        historyError.textContent = `Error: ${err.message}`;
    } finally {
        historyLoading.style.display = 'none';
    }
}

async function showHistoryDetail(record) {
    historyList.style.display = 'none';
    historyDetail.style.display = 'block';

    // Limpiar galería anterior
    historyDetailImage.style.display = 'none';
    const oldGallery = document.getElementById('historyImageGallery');
    if (oldGallery) oldGallery.remove();

    // Crear contenedor de galería
    const gallery = document.createElement('div');
    gallery.id = 'historyImageGallery';
    gallery.style.display = 'grid';
    gallery.style.gridTemplateColumns = 'repeat(auto-fit, minmax(150px, 1fr))';
    gallery.style.gap = '10px';
    gallery.style.marginBottom = '15px';
    historyDetailImage.parentNode.insertBefore(gallery, historyDetailImage);

    try {
        const res = await fetch(`/api/v1/detection/history/${record.id}/images`);
        if (res.ok) {
            const data = await res.json();
            data.filenames.forEach(filename => {
                const img = document.createElement('img');
                img.src = `/api/v1/detection/history/${record.id}/images/${filename}`;
                img.alt = filename;
                img.title = filename;
                img.style.width = '100%';
                img.style.borderRadius = '8px';
                img.style.cursor = 'pointer';
                img.onclick = () => openLightbox(img.src);
                gallery.appendChild(img);
            });
        }
    } catch (err) {
        console.error('Error cargando imágenes:', err);
    }

    let html = `<h3>${record.image_filename}</h3>
        <p style="color: #666; margin-bottom: 15px;">
            ${new Date(record.timestamp).toLocaleString('es-DO')}
        </p>`;

    record.colors.forEach(c => {
        html += `<div class="channel-result detected">
            <div class="channel-name">Canal ${c.name}</div>
            <div class="channel-details">
                <div>Posición X: ${c.coordinates.x} px</div>
                <div>Posición Y: ${c.coordinates.y} px</div>
                <div>Confianza: ${(c.confidence * 100).toFixed(2)}%</div>
                ${c.extra && c.extra.scale ? `<div>Escala: ${c.extra.scale}x</div>` : ''}
            </div>
        </div>`;
    });

    if (record.metadata && Object.keys(record.metadata).length > 0) {
        html += `<div class="channel-result">
            <div class="channel-name">Metadata</div>
            <div class="channel-details">
                ${Object.entries(record.metadata).map(([k, v]) => `<div>${k}: ${v}</div>`).join('')}
            </div>
        </div>`;
    }

    historyDetailContent.innerHTML = html;
}

// ============ LIGHTBOX ============
// Compartido: usado tanto por el historial como por la galería
// de resultados en imagen.js
const lightboxOverlay = document.getElementById('lightboxOverlay');
const lightboxImage = document.getElementById('lightboxImage');
const lightboxClose = document.getElementById('lightboxClose');

function openLightbox(src) {
    lightboxImage.src = src;
    lightboxOverlay.classList.add('show');
}

function closeLightbox() {
    lightboxOverlay.classList.remove('show');
    lightboxImage.src = '';
}

lightboxClose.addEventListener('click', closeLightbox);

// Cerrar al hacer clic fuera de la imagen
lightboxOverlay.addEventListener('click', (e) => {
    if (e.target === lightboxOverlay) {
        closeLightbox();
    }
});

// Cerrar con la tecla Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && lightboxOverlay.classList.contains('show')) {
        closeLightbox();
    }
});
