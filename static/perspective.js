const perspectiveState = {
    image: null, points: [], draggingPoint: -1, scale: 1, outputCanvas: null, outputSize: null
};

document.getElementById('perspectiveUpload').addEventListener('click', () => {
    document.getElementById('perspectiveFileInput').click();
});

document.getElementById('perspectiveFileInput').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
        alert('File size must be less than 5MB');
        e.target.value = '';
        return;
    }
    loadPerspectiveImage(file);
});

function loadPerspectiveImage(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
            perspectiveState.image = img;
            initPerspectiveEditor();
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

function initPerspectiveEditor() {
    const img = perspectiveState.image;
    const maxWidth = Math.min(600, window.innerWidth - 48);
    const scale = img.width > maxWidth ? maxWidth / img.width : 1;
    perspectiveState.scale = scale;
    const displayW = Math.round(img.width * scale);
    const displayH = Math.round(img.height * scale);

    const canvas = document.getElementById('perspectiveCanvas');
    const preview = document.getElementById('perspectivePreview');
    canvas.width = displayW;
    canvas.height = displayH;
    preview.width = displayW;
    preview.height = displayH;

    const rectW = displayW / 2, rectH = displayH / 2;
    const offsetX = (displayW - rectW) / 2, offsetY = (displayH - rectH) / 2;
    perspectiveState.points = [
        {x: offsetX, y: offsetY},
        {x: offsetX + rectW, y: offsetY},
        {x: offsetX + rectW, y: offsetY + rectH},
        {x: offsetX, y: offsetY + rectH}
    ];

    document.getElementById('perspectiveUpload').style.display = 'none';
    document.getElementById('perspectiveEditor').style.display = 'block';

    setupPerspectiveCanvas();
    drawPerspective();
    updatePerspectivePreview();
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

function findPoint(pos, points, threshold = 15) {
    for (let i = 0; i < points.length; i++) {
        const dx = pos.x - points[i].x, dy = pos.y - points[i].y;
        if (Math.sqrt(dx*dx + dy*dy) < threshold) return i;
    }
    return -1;
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

function setupPerspectiveCanvas() {
    const canvas = document.getElementById('perspectiveCanvas');

    // Mouse events
    canvas.addEventListener('mousedown', (e) => {
        const pos = getCanvasPos(canvas, e);
        perspectiveState.draggingPoint = findPoint(pos, perspectiveState.points);
        if (perspectiveState.draggingPoint >= 0) canvas.style.cursor = 'grabbing';
    });
    canvas.addEventListener('mousemove', (e) => {
        const pos = getCanvasPos(canvas, e);
        if (perspectiveState.draggingPoint >= 0) {
            perspectiveState.points[perspectiveState.draggingPoint] = {
                x: Math.max(0, Math.min(canvas.width, pos.x)),
                y: Math.max(0, Math.min(canvas.height, pos.y))
            };
            drawPerspective();
            updatePerspectivePreview();
        } else {
            canvas.style.cursor = findPoint(pos, perspectiveState.points) >= 0 ? 'grab' : 'crosshair';
        }
    });
    canvas.addEventListener('mouseup', () => {
        perspectiveState.draggingPoint = -1;
        canvas.style.cursor = 'crosshair';
    });
    document.addEventListener('mouseup', () => { perspectiveState.draggingPoint = -1; });

    // Touch events
    canvas.addEventListener('touchstart', (e) => {
        e.preventDefault();
        const pos = getTouchPos(canvas, e);
        perspectiveState.draggingPoint = findPoint(pos, perspectiveState.points, 25);
    }, { passive: false });
    canvas.addEventListener('touchmove', (e) => {
        e.preventDefault();
        if (perspectiveState.draggingPoint >= 0) {
            const pos = getTouchPos(canvas, e);
            perspectiveState.points[perspectiveState.draggingPoint] = {
                x: Math.max(0, Math.min(canvas.width, pos.x)),
                y: Math.max(0, Math.min(canvas.height, pos.y))
            };
            drawPerspective();
            updatePerspectivePreview();
        }
    }, { passive: false });
    canvas.addEventListener('touchend', () => {
        perspectiveState.draggingPoint = -1;
    });
}

function drawPerspective() {
    const canvas = document.getElementById('perspectiveCanvas');
    const ctx = canvas.getContext('2d');
    const points = perspectiveState.points;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(perspectiveState.image, 0, 0, canvas.width, canvas.height);

    ctx.fillStyle = 'rgba(0, 102, 255, 0.15)';
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    points.forEach(p => ctx.lineTo(p.x, p.y));
    ctx.closePath();
    ctx.fill();

    ctx.strokeStyle = '#0066ff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    points.forEach(p => ctx.lineTo(p.x, p.y));
    ctx.closePath();
    ctx.stroke();

    const labels = ['1', '2', '3', '4'];
    points.forEach((p, i) => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#0066ff';
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.fillStyle = '#0066ff';
        ctx.font = 'bold 10px Arial';
        ctx.fillText(labels[i], p.x + 8, p.y - 8);
    });

    const scale = perspectiveState.scale;
    const coordsHtml = points.map((p, i) => {
        const realX = Math.round(p.x / scale), realY = Math.round(p.y / scale);
        return `${['TL','TR','BR','BL'][i]}: (${realX}, ${realY})`;
    }).join(' &nbsp; ');
    document.getElementById('coordsDisplay').innerHTML = coordsHtml;
}

function updatePerspectivePreview() {
    const canvas = document.getElementById('perspectivePreview');
    const ctx = canvas.getContext('2d');
    const sourceCanvas = document.getElementById('perspectiveCanvas');
    const points = perspectiveState.points;
    const scale = perspectiveState.scale;

    canvas.width = sourceCanvas.width;
    canvas.height = sourceCanvas.height;

    const realPts = points.map(p => ({x: p.x / scale, y: p.y / scale}));
    const outputW = Math.round(Math.max(
        Math.hypot(realPts[1].x - realPts[0].x, realPts[1].y - realPts[0].y),
        Math.hypot(realPts[2].x - realPts[3].x, realPts[2].y - realPts[3].y)
    ));
    const outputH = Math.round(Math.max(
        Math.hypot(realPts[3].x - realPts[0].x, realPts[3].y - realPts[0].y),
        Math.hypot(realPts[2].x - realPts[1].x, realPts[2].y - realPts[1].y)
    ));

    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = outputW;
    tempCanvas.height = outputH;
    const tempCtx = tempCanvas.getContext('2d');

    const H = computeHomography(
        [{x:0,y:0}, {x:outputW,y:0}, {x:outputW,y:outputH}, {x:0,y:outputH}],
        points
    );

    const srcCanvas = document.createElement('canvas');
    srcCanvas.width = sourceCanvas.width;
    srcCanvas.height = sourceCanvas.height;
    srcCanvas.getContext('2d').drawImage(perspectiveState.image, 0, 0, srcCanvas.width, srcCanvas.height);
    const srcData = srcCanvas.getContext('2d').getImageData(0, 0, srcCanvas.width, srcCanvas.height);
    const dstData = tempCtx.createImageData(outputW, outputH);

    for (let py = 0; py < outputH; py++) {
        for (let px = 0; px < outputW; px++) {
            const src = applyHomography(H, px, py);
            const sx = Math.round(src.x), sy = Math.round(src.y);
            if (sx >= 0 && sx < srcCanvas.width && sy >= 0 && sy < srcCanvas.height) {
                const srcIdx = (sy * srcCanvas.width + sx) * 4;
                const dstIdx = (py * outputW + px) * 4;
                dstData.data[dstIdx] = srcData.data[srcIdx];
                dstData.data[dstIdx+1] = srcData.data[srcIdx+1];
                dstData.data[dstIdx+2] = srcData.data[srcIdx+2];
                dstData.data[dstIdx+3] = 255;
            }
        }
    }
    tempCtx.putImageData(dstData, 0, 0);

    perspectiveState.outputCanvas = tempCanvas;
    perspectiveState.outputSize = {w: outputW, h: outputH};

    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    const fitScale = Math.min(canvas.width / outputW, canvas.height / outputH);
    const drawW = outputW * fitScale, drawH = outputH * fitScale;
    const drawX = (canvas.width - drawW) / 2, drawY = (canvas.height - drawH) / 2;
    ctx.drawImage(tempCanvas, drawX, drawY, drawW, drawH);

    document.getElementById('perspectivePreviewSize').textContent = `${outputW} x ${outputH}`;
}

function solve(A, b) {
    const n = b.length;
    const aug = A.map((row, i) => [...row, b[i]]);
    for (let col = 0; col < n; col++) {
        let maxRow = col;
        for (let row = col + 1; row < n; row++) {
            if (Math.abs(aug[row][col]) > Math.abs(aug[maxRow][col])) maxRow = row;
        }
        [aug[col], aug[maxRow]] = [aug[maxRow], aug[col]];
        if (Math.abs(aug[col][col]) < 1e-10) continue;
        for (let row = col + 1; row < n; row++) {
            const factor = aug[row][col] / aug[col][col];
            for (let j = col; j <= n; j++) aug[row][j] -= factor * aug[col][j];
        }
    }
    const x = new Array(n).fill(0);
    for (let i = n - 1; i >= 0; i--) {
        x[i] = aug[i][n];
        for (let j = i + 1; j < n; j++) x[i] -= aug[i][j] * x[j];
        x[i] /= aug[i][i];
    }
    return x;
}

function computeHomography(src, dst) {
    const A = [], b = [];
    for (let i = 0; i < 4; i++) {
        const sx = src[i].x, sy = src[i].y, dx = dst[i].x, dy = dst[i].y;
        A.push([sx, sy, 1, 0, 0, 0, -dx*sx, -dx*sy]);
        A.push([0, 0, 0, sx, sy, 1, -dy*sx, -dy*sy]);
        b.push(dx); b.push(dy);
    }
    const h = solve(A, b);
    return [[h[0], h[1], h[2]], [h[3], h[4], h[5]], [h[6], h[7], 1]];
}

function applyHomography(H, x, y) {
    const d = H[2][0]*x + H[2][1]*y + H[2][2];
    return { x: (H[0][0]*x + H[0][1]*y + H[0][2]) / d, y: (H[1][0]*x + H[1][1]*y + H[1][2]) / d };
}

document.getElementById('perspectiveReset').addEventListener('click', () => {
    const canvas = document.getElementById('perspectiveCanvas');
    const rectW = canvas.width / 2, rectH = canvas.height / 2;
    const offsetX = (canvas.width - rectW) / 2, offsetY = (canvas.height - rectH) / 2;
    perspectiveState.points = [
        {x: offsetX, y: offsetY},
        {x: offsetX + rectW, y: offsetY},
        {x: offsetX + rectW, y: offsetY + rectH},
        {x: offsetX, y: offsetY + rectH}
    ];
    drawPerspective();
    updatePerspectivePreview();
});

document.getElementById('perspectiveDownload').addEventListener('click', () => {
    if (perspectiveState.outputCanvas) {
        const {w, h} = perspectiveState.outputSize;
        const link = document.createElement('a');
        link.download = `transformed_${w}x${h}.png`;
        link.href = perspectiveState.outputCanvas.toDataURL('image/png');
        link.click();
    }
});
