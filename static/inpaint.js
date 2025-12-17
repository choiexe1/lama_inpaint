const inpaintState = {
    image: null, imageData: null, maskHistory: [], historyIndex: -1, isDrawing: false, brushSize: 30, resultData: null
};

function showError(msg) {
    const el = document.getElementById('errorDisplay');
    el.textContent = msg;
    el.style.display = 'block';
}

document.getElementById('inpaintUpload').addEventListener('click', () => {
    document.getElementById('inpaintFileInput').click();
});

document.getElementById('inpaintFileInput').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
        alert('File size must be less than 5MB');
        e.target.value = '';
        return;
    }
    loadInpaintImage(file);
});

function loadInpaintImage(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        inpaintState.imageData = e.target.result;
        const img = new Image();
        img.onload = () => {
            inpaintState.image = img;
            initInpaintEditor();
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

function initInpaintEditor() {
    const img = inpaintState.image;
    const maxWidth = Math.min(600, window.innerWidth - 48);
    const scale = img.width > maxWidth ? maxWidth / img.width : 1;
    const displayW = Math.round(img.width * scale);
    const displayH = Math.round(img.height * scale);

    const maskCanvas = document.getElementById('maskCanvas');
    const resultCanvas = document.getElementById('resultCanvas');
    maskCanvas.width = displayW;
    maskCanvas.height = displayH;
    resultCanvas.width = displayW;
    resultCanvas.height = displayH;

    document.getElementById('maskContainer').style.width = displayW + 'px';
    document.getElementById('maskContainer').style.height = displayH + 'px';
    document.getElementById('resultContainer').style.width = displayW + 'px';
    document.getElementById('resultContainer').style.height = displayH + 'px';
    document.getElementById('resultPlaceholder').style.width = displayW + 'px';
    document.getElementById('resultPlaceholder').style.height = displayH + 'px';

    inpaintState.maskLayer = document.createElement('canvas');
    inpaintState.maskLayer.width = displayW;
    inpaintState.maskLayer.height = displayH;
    const maskCtx = inpaintState.maskLayer.getContext('2d');
    maskCtx.fillStyle = '#000';
    maskCtx.fillRect(0, 0, displayW, displayH);

    inpaintState.maskHistory = [maskCtx.getImageData(0, 0, displayW, displayH)];
    inpaintState.historyIndex = 0;

    document.getElementById('inpaintUpload').style.display = 'none';
    document.getElementById('inpaintEditor').style.display = 'block';

    setupInpaintCanvas();
    renderMask();
}

function getCanvasPos(canvas, e) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
        x: (e.clientX - rect.left) * scaleX,
        y: (e.clientY - rect.top) * scaleY
    };
}

function getTouchPos(canvas, e) {
    const rect = canvas.getBoundingClientRect();
    const touch = e.touches[0] || e.changedTouches[0];
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
        x: (touch.clientX - rect.left) * scaleX,
        y: (touch.clientY - rect.top) * scaleY
    };
}

function setupInpaintCanvas() {
    const canvas = document.getElementById('maskCanvas');
    const brushPreview = document.getElementById('brushPreview');

    // Mouse events
    canvas.addEventListener('mouseenter', () => {
        brushPreview.style.display = 'block';
        updateBrushPreview();
    });
    canvas.addEventListener('mouseleave', () => {
        brushPreview.style.display = 'none';
        inpaintState.isDrawing = false;
    });
    canvas.addEventListener('mousemove', (e) => {
        const rect = canvas.getBoundingClientRect();
        brushPreview.style.left = (e.clientX - rect.left) + 'px';
        brushPreview.style.top = (e.clientY - rect.top) + 'px';
        if (inpaintState.isDrawing) {
            const pos = getCanvasPos(canvas, e);
            paintMask(pos.x, pos.y);
            renderMask();
        }
    });
    canvas.addEventListener('mousedown', (e) => {
        inpaintState.isDrawing = true;
        const pos = getCanvasPos(canvas, e);
        paintMask(pos.x, pos.y);
        renderMask();
    });
    canvas.addEventListener('mouseup', () => {
        if (inpaintState.isDrawing) saveHistory();
        inpaintState.isDrawing = false;
    });
    document.addEventListener('mouseup', () => {
        if (inpaintState.isDrawing) saveHistory();
        inpaintState.isDrawing = false;
    });

    // Touch events
    canvas.addEventListener('touchstart', (e) => {
        e.preventDefault();
        inpaintState.isDrawing = true;
        const pos = getTouchPos(canvas, e);
        paintMask(pos.x, pos.y);
        renderMask();
    }, { passive: false });
    canvas.addEventListener('touchmove', (e) => {
        e.preventDefault();
        if (inpaintState.isDrawing) {
            const pos = getTouchPos(canvas, e);
            paintMask(pos.x, pos.y);
            renderMask();
        }
    }, { passive: false });
    canvas.addEventListener('touchend', () => {
        if (inpaintState.isDrawing) saveHistory();
        inpaintState.isDrawing = false;
    });

    const brushSlider = document.getElementById('brushSize');
    const brushNumInput = document.getElementById('brushSizeNum');
    brushSlider.addEventListener('input', (e) => {
        inpaintState.brushSize = parseInt(e.target.value);
        brushNumInput.value = e.target.value;
        updateBrushPreview();
    });
    brushNumInput.addEventListener('input', (e) => {
        let val = parseInt(e.target.value) || 5;
        val = Math.max(5, Math.min(100, val));
        inpaintState.brushSize = val;
        brushSlider.value = val;
        updateBrushPreview();
    });

    document.getElementById('maskColor').addEventListener('input', () => {
        renderMask();
    });

    document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
            e.preventDefault();
            if (e.shiftKey) redo();
            else undo();
        }
    });
}

function updateBrushPreview() {
    const brushPreview = document.getElementById('brushPreview');
    const size = inpaintState.brushSize;
    brushPreview.style.width = size + 'px';
    brushPreview.style.height = size + 'px';
}

function paintMask(x, y) {
    const maskCtx = inpaintState.maskLayer.getContext('2d');
    maskCtx.fillStyle = '#fff';
    maskCtx.beginPath();
    maskCtx.arc(x, y, inpaintState.brushSize / 2, 0, Math.PI * 2);
    maskCtx.fill();
}

function renderMask() {
    const canvas = document.getElementById('maskCanvas');
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(inpaintState.image, 0, 0, canvas.width, canvas.height);

    ctx.globalAlpha = 0.5;
    const maskData = inpaintState.maskLayer.getContext('2d').getImageData(0, 0, canvas.width, canvas.height);
    const overlay = document.createElement('canvas');
    overlay.width = canvas.width;
    overlay.height = canvas.height;
    const overlayCtx = overlay.getContext('2d');
    const overlayData = overlayCtx.createImageData(canvas.width, canvas.height);

    const maskColorHex = document.getElementById('maskColor').value;
    const r = parseInt(maskColorHex.slice(1,3), 16);
    const g = parseInt(maskColorHex.slice(3,5), 16);
    const b = parseInt(maskColorHex.slice(5,7), 16);

    for (let i = 0; i < maskData.data.length; i += 4) {
        if (maskData.data[i] > 128) {
            overlayData.data[i] = r;
            overlayData.data[i+1] = g;
            overlayData.data[i+2] = b;
            overlayData.data[i+3] = 255;
        }
    }
    overlayCtx.putImageData(overlayData, 0, 0);
    ctx.drawImage(overlay, 0, 0);
    ctx.globalAlpha = 1.0;
}

function saveHistory() {
    const maskCtx = inpaintState.maskLayer.getContext('2d');
    const data = maskCtx.getImageData(0, 0, inpaintState.maskLayer.width, inpaintState.maskLayer.height);
    inpaintState.maskHistory = inpaintState.maskHistory.slice(0, inpaintState.historyIndex + 1);
    inpaintState.maskHistory.push(data);
    if (inpaintState.maskHistory.length > 50) inpaintState.maskHistory.shift();
    inpaintState.historyIndex = inpaintState.maskHistory.length - 1;
}

function undo() {
    if (inpaintState.historyIndex > 0) {
        inpaintState.historyIndex--;
        const maskCtx = inpaintState.maskLayer.getContext('2d');
        maskCtx.putImageData(inpaintState.maskHistory[inpaintState.historyIndex], 0, 0);
        renderMask();
    }
}

function redo() {
    if (inpaintState.historyIndex < inpaintState.maskHistory.length - 1) {
        inpaintState.historyIndex++;
        const maskCtx = inpaintState.maskLayer.getContext('2d');
        maskCtx.putImageData(inpaintState.maskHistory[inpaintState.historyIndex], 0, 0);
        renderMask();
    }
}

document.getElementById('clearMask').addEventListener('click', () => {
    const maskCtx = inpaintState.maskLayer.getContext('2d');
    maskCtx.fillStyle = '#000';
    maskCtx.fillRect(0, 0, inpaintState.maskLayer.width, inpaintState.maskLayer.height);
    saveHistory();
    renderMask();
});

document.getElementById('undoMask').addEventListener('click', undo);
document.getElementById('redoMask').addEventListener('click', redo);
document.getElementById('resetInpaint').addEventListener('click', () => location.reload());

document.getElementById('runInpaint').addEventListener('click', async () => {
    const loading = document.getElementById('loading');
    loading.classList.remove('hidden');
    try {
        const maskCanvas = inpaintState.maskLayer;
        const maskData = maskCanvas.toDataURL('image/png');
        const response = await fetch('/api/inpaint', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: `image=${encodeURIComponent(inpaintState.imageData)}&mask=${encodeURIComponent(maskData)}`
        });
        const data = await response.json();
        if (data.error) {
            showError(data.error);
        } else {
            const resultImg = new Image();
            resultImg.onload = () => {
                const resultCanvas = document.getElementById('resultCanvas');
                const ctx = resultCanvas.getContext('2d');
                ctx.drawImage(resultImg, 0, 0, resultCanvas.width, resultCanvas.height);
                document.getElementById('resultPlaceholder').style.display = 'none';
                document.getElementById('downloadResult').style.display = 'inline-block';
                inpaintState.resultData = data.result;
            };
            resultImg.src = data.result;
        }
    } catch (e) {
        showError('Error: ' + e.message);
    } finally {
        loading.classList.add('hidden');
    }
});

document.getElementById('downloadResult').addEventListener('click', () => {
    if (inpaintState.resultData) {
        const link = document.createElement('a');
        link.download = 'inpainted.png';
        link.href = inpaintState.resultData;
        link.click();
    }
});
