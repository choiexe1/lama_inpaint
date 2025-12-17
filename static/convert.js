const convertState = {
    image: null,
    originalFile: null,
    convertedBlob: null
};

document.getElementById('convertUpload').addEventListener('click', () => {
    document.getElementById('convertFileInput').click();
});

document.getElementById('convertFileInput').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
        alert('File size must be less than 5MB');
        e.target.value = '';
        return;
    }
    loadConvertImage(file);
});

function loadConvertImage(file) {
    convertState.originalFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
            convertState.image = img;
            initConvertEditor();
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

function initConvertEditor() {
    const img = convertState.image;
    const maxWidth = Math.min(500, window.innerWidth - 48);
    const scale = img.width > maxWidth ? maxWidth / img.width : 1;
    const displayW = Math.round(img.width * scale);
    const displayH = Math.round(img.height * scale);

    const originalCanvas = document.getElementById('originalCanvas');
    const convertedCanvas = document.getElementById('convertedCanvas');

    originalCanvas.width = displayW;
    originalCanvas.height = displayH;
    convertedCanvas.width = displayW;
    convertedCanvas.height = displayH;

    const ctx = originalCanvas.getContext('2d');
    ctx.drawImage(img, 0, 0, displayW, displayH);

    // Show original info
    const originalSize = convertState.originalFile.size;
    const originalFormat = convertState.originalFile.type || 'unknown';
    document.getElementById('originalInfo').innerHTML =
        `${formatFileSize(originalSize)} · ${img.width}×${img.height} · ${getFormatName(originalFormat)}`;

    document.getElementById('convertUpload').style.display = 'none';
    document.getElementById('convertEditor').style.display = 'block';

    updateQualityVisibility();
    convertImage();
}

function getFormatName(mimeType) {
    const formats = {
        'image/jpeg': 'JPEG',
        'image/png': 'PNG',
        'image/webp': 'WebP',
        'image/avif': 'AVIF',
        'image/gif': 'GIF',
        'image/bmp': 'BMP'
    };
    return formats[mimeType] || mimeType.split('/')[1]?.toUpperCase() || 'Unknown';
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

function updateQualityVisibility() {
    const format = document.getElementById('outputFormat').value;
    const qualityRow = document.getElementById('qualityRow');
    // PNG, GIF, BMP don't support quality
    if (format === 'image/png' || format === 'image/gif' || format === 'image/bmp') {
        qualityRow.style.display = 'none';
    } else {
        qualityRow.style.display = 'flex';
    }
}

async function convertImage() {
    const img = convertState.image;
    const format = document.getElementById('outputFormat').value;
    const quality = parseInt(document.getElementById('quality').value) / 100;

    // Create full-size canvas for conversion
    const fullCanvas = document.createElement('canvas');
    fullCanvas.width = img.width;
    fullCanvas.height = img.height;
    const fullCtx = fullCanvas.getContext('2d');
    fullCtx.drawImage(img, 0, 0);

    // Convert to blob
    let blob;
    try {
        if (format === 'image/png' || format === 'image/gif' || format === 'image/bmp') {
            blob = await new Promise(resolve => fullCanvas.toBlob(resolve, format));
        } else {
            blob = await new Promise(resolve => fullCanvas.toBlob(resolve, format, quality));
        }
    } catch (e) {
        // Fallback for unsupported formats
        blob = await new Promise(resolve => fullCanvas.toBlob(resolve, 'image/png'));
        document.getElementById('convertedInfo').innerHTML =
            `Format not supported by browser. Showing PNG instead.`;
        return;
    }

    if (!blob) {
        document.getElementById('convertedInfo').innerHTML = 'Conversion failed. Format may not be supported.';
        return;
    }

    convertState.convertedBlob = blob;

    // Draw preview
    const convertedCanvas = document.getElementById('convertedCanvas');
    const ctx = convertedCanvas.getContext('2d');
    const previewImg = new Image();
    previewImg.onload = () => {
        ctx.clearRect(0, 0, convertedCanvas.width, convertedCanvas.height);
        ctx.drawImage(previewImg, 0, 0, convertedCanvas.width, convertedCanvas.height);
        URL.revokeObjectURL(previewImg.src);
    };
    previewImg.src = URL.createObjectURL(blob);

    // Show converted info
    const convertedSize = blob.size;
    document.getElementById('convertedInfo').innerHTML =
        `${formatFileSize(convertedSize)} · ${img.width}×${img.height} · ${getFormatName(format)}`;

    // Show size comparison
    updateSizeComparison(convertState.originalFile.size, convertedSize);
}

function updateSizeComparison(originalSize, convertedSize) {
    const comparison = document.getElementById('sizeComparison');
    const barOriginal = document.getElementById('barOriginal');
    const barConverted = document.getElementById('barConverted');
    const comparisonText = document.getElementById('comparisonText');

    comparison.style.display = 'block';

    const maxSize = Math.max(originalSize, convertedSize);
    const originalPercent = (originalSize / maxSize) * 100;
    const convertedPercent = (convertedSize / maxSize) * 100;

    barOriginal.style.width = originalPercent + '%';
    barConverted.style.width = convertedPercent + '%';

    const diff = originalSize - convertedSize;
    const diffPercent = ((diff / originalSize) * 100).toFixed(1);

    if (diff > 0) {
        comparisonText.innerHTML = `<span class="size-reduced">↓ ${formatFileSize(diff)} smaller (${diffPercent}% reduction)</span>`;
        barConverted.className = 'bar-converted smaller';
    } else if (diff < 0) {
        comparisonText.innerHTML = `<span class="size-increased">↑ ${formatFileSize(-diff)} larger (${(-diffPercent)}% increase)</span>`;
        barConverted.className = 'bar-converted larger';
    } else {
        comparisonText.innerHTML = `<span>Same size</span>`;
        barConverted.className = 'bar-converted';
    }
}

// Event listeners
document.getElementById('outputFormat').addEventListener('change', () => {
    updateQualityVisibility();
    convertImage();
});

document.getElementById('quality').addEventListener('input', (e) => {
    document.getElementById('qualityValue').textContent = e.target.value + '%';
    convertImage();
});

document.getElementById('convertReset').addEventListener('click', () => {
    location.reload();
});

document.getElementById('convertDownload').addEventListener('click', () => {
    if (convertState.convertedBlob) {
        const format = document.getElementById('outputFormat').value;
        const ext = format.split('/')[1];
        const link = document.createElement('a');
        link.download = `converted.${ext}`;
        link.href = URL.createObjectURL(convertState.convertedBlob);
        link.click();
        URL.revokeObjectURL(link.href);
    }
});
