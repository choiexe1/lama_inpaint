import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import cv2
from PIL import Image
import base64
import io

st.set_page_config(page_title="이미지 도구", layout="wide")

# 세션 상태 초기화
if 'transformed_image' not in st.session_state:
    st.session_state.transformed_image = None
if 'points_data' not in st.session_state:
    st.session_state.points_data = None

# 사이드바 페이지 선택
page = st.sidebar.radio("페이지 선택", ["원근변환 크롭", "인페인트"])


def get_perspective_canvas_html(img_base64, full_img_base64, display_width, display_height, scale, full_scale):
    """4점 드래그 가능한 캔버스 + 실시간 프리뷰 HTML/JS"""

    # 초기 4점 (이미지 절반 크기, 중앙 배치)
    rect_w = display_width // 2
    rect_h = display_height // 2
    offset_x = (display_width - rect_w) // 2
    offset_y = (display_height - rect_h) // 2

    return f"""
    <style>
        .perspective-container {{
            display: flex;
            gap: 24px;
            align-items: flex-start;
            width: 100%;
        }}
        .panel {{
            flex: 1;
            min-width: 0;
        }}
        .panel-label {{
            font-size: 11px;
            color: #888;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .canvas-container {{
            width: 100%;
            aspect-ratio: {display_width} / {display_height};
            border: 1px solid #333;
            background: #1a1a1a;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            position: relative;
        }}
        .canvas-container canvas {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
        }}
        .info-text {{
            margin-top: 6px;
            font-family: monospace;
            font-size: 11px;
            text-align: center;
        }}
        .button-group {{
            margin-top: 12px;
            display: flex;
            gap: 8px;
            align-items: center;
        }}
        .btn-reset {{
            padding: 8px 16px;
            background: transparent;
            color: #888;
            border: 1px solid #444;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }}
        .btn-download {{
            padding: 8px 20px;
            background: #0066ff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
        }}
    </style>
    <div class="perspective-container">
        <div class="panel">
            <div class="panel-label">Source</div>
            <div class="canvas-container" id="sourceContainer">
                <canvas id="perspectiveCanvas" width="{display_width}" height="{display_height}" style="cursor: crosshair;"></canvas>
            </div>
            <div id="coordsDisplay" class="info-text" style="color: #0066cc;"></div>
        </div>
        <div class="panel">
            <div class="panel-label">Preview</div>
            <div class="canvas-container" id="previewContainer">
                <canvas id="previewCanvas"></canvas>
            </div>
            <div id="previewSize" class="info-text" style="color: #666;"></div>
            <div class="button-group">
                <button id="resetBtn" class="btn-reset">Reset</button>
                <button id="downloadBtn" class="btn-download">Download</button>
                <span id="downloadStatus" style="color: #28a745; font-size: 11px;"></span>
            </div>
        </div>
        <input type="hidden" id="pointsData" value="">
    </div>

    <script>
    (function() {{
        const canvas = document.getElementById('perspectiveCanvas');
        const ctx = canvas.getContext('2d');
        const previewCanvas = document.getElementById('previewCanvas');
        const previewCtx = previewCanvas.getContext('2d');
        const coordsDisplay = document.getElementById('coordsDisplay');
        const pointsDataInput = document.getElementById('pointsData');
        const previewSize = document.getElementById('previewSize');
        const resetBtn = document.getElementById('resetBtn');

        const scale = {scale};
        const fullScale = {full_scale};
        const baseWidth = {display_width};
        const baseHeight = {display_height};

        // 초기 포인트 저장 (리셋용)
        const initialPoints = [
            {{x: {offset_x}, y: {offset_y}}},
            {{x: {offset_x + rect_w}, y: {offset_y}}},
            {{x: {offset_x + rect_w}, y: {offset_y + rect_h}}},
            {{x: {offset_x}, y: {offset_y + rect_h}}}
        ];

        let img = new Image();
        let points = [
            {{x: {offset_x}, y: {offset_y}}},
            {{x: {offset_x + rect_w}, y: {offset_y}}},
            {{x: {offset_x + rect_w}, y: {offset_y + rect_h}}},
            {{x: {offset_x}, y: {offset_y + rect_h}}}
        ];
        let draggingPoint = -1;
        const pointRadius = 4;

        // 원본 이미지만 담는 별도 캔버스 (오버레이 없이)
        const imgCanvas = document.createElement('canvas');
        imgCanvas.width = {display_width};
        imgCanvas.height = {display_height};
        const imgCtx = imgCanvas.getContext('2d');

        img.onload = function() {{
            // 원본 이미지를 숨겨진 캔버스에 그리기
            imgCtx.drawImage(img, 0, 0, imgCanvas.width, imgCanvas.height);
            draw();
            updatePreview();
        }};
        img.src = '{img_base64}';

        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

            // 반투명 오버레이
            ctx.fillStyle = 'rgba(0, 102, 255, 0.15)';
            ctx.beginPath();
            ctx.moveTo(points[0].x, points[0].y);
            for (let i = 1; i < 4; i++) {{
                ctx.lineTo(points[i].x, points[i].y);
            }}
            ctx.closePath();
            ctx.fill();

            // 선 그리기
            ctx.strokeStyle = '#0066ff';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(points[0].x, points[0].y);
            for (let i = 1; i < 4; i++) {{
                ctx.lineTo(points[i].x, points[i].y);
            }}
            ctx.closePath();
            ctx.stroke();

            // 점 그리기
            const labels = ['1', '2', '3', '4'];
            points.forEach((p, i) => {{
                ctx.beginPath();
                ctx.arc(p.x, p.y, pointRadius, 0, Math.PI * 2);
                ctx.fillStyle = '#0066ff';
                ctx.fill();
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 2;
                ctx.stroke();

                ctx.fillStyle = '#0066ff';
                ctx.font = 'bold 10px Arial';
                ctx.textAlign = 'left';
                ctx.textBaseline = 'top';
                ctx.fillText(labels[i], p.x + 8, p.y - 12);
            }});

            updateCoords();
        }}

        // Gaussian elimination for solving linear system
        function solve(A, b) {{
            const n = b.length;
            const aug = A.map((row, i) => [...row, b[i]]);

            for (let col = 0; col < n; col++) {{
                let maxRow = col;
                for (let row = col + 1; row < n; row++) {{
                    if (Math.abs(aug[row][col]) > Math.abs(aug[maxRow][col])) {{
                        maxRow = row;
                    }}
                }}
                [aug[col], aug[maxRow]] = [aug[maxRow], aug[col]];

                if (Math.abs(aug[col][col]) < 1e-10) continue;

                for (let row = col + 1; row < n; row++) {{
                    const factor = aug[row][col] / aug[col][col];
                    for (let j = col; j <= n; j++) {{
                        aug[row][j] -= factor * aug[col][j];
                    }}
                }}
            }}

            const x = new Array(n).fill(0);
            for (let i = n - 1; i >= 0; i--) {{
                x[i] = aug[i][n];
                for (let j = i + 1; j < n; j++) {{
                    x[i] -= aug[i][j] * x[j];
                }}
                x[i] /= aug[i][i];
            }}
            return x;
        }}

        function computeHomography(src, dst) {{
            const A = [];
            const b = [];
            for (let i = 0; i < 4; i++) {{
                const sx = src[i].x, sy = src[i].y;
                const dx = dst[i].x, dy = dst[i].y;
                A.push([sx, sy, 1, 0, 0, 0, -dx*sx, -dx*sy]);
                A.push([0, 0, 0, sx, sy, 1, -dy*sx, -dy*sy]);
                b.push(dx);
                b.push(dy);
            }}
            const h = solve(A, b);
            return [[h[0], h[1], h[2]], [h[3], h[4], h[5]], [h[6], h[7], 1]];
        }}

        function applyHomography(H, x, y) {{
            const d = H[2][0]*x + H[2][1]*y + H[2][2];
            return {{
                x: (H[0][0]*x + H[0][1]*y + H[0][2]) / d,
                y: (H[1][0]*x + H[1][1]*y + H[1][2]) / d
            }};
        }}

        function getOutputSize() {{
            // 4점의 바운딩 박스로 출력 크기 계산 (실제 좌표 기준)
            const realPts = points.map(p => ({{x: p.x / scale, y: p.y / scale}}));
            const width = Math.max(
                Math.sqrt(Math.pow(realPts[1].x - realPts[0].x, 2) + Math.pow(realPts[1].y - realPts[0].y, 2)),
                Math.sqrt(Math.pow(realPts[2].x - realPts[3].x, 2) + Math.pow(realPts[2].y - realPts[3].y, 2))
            );
            const height = Math.max(
                Math.sqrt(Math.pow(realPts[3].x - realPts[0].x, 2) + Math.pow(realPts[3].y - realPts[0].y, 2)),
                Math.sqrt(Math.pow(realPts[2].x - realPts[1].x, 2) + Math.pow(realPts[2].y - realPts[1].y, 2))
            );
            return {{ w: Math.round(width), h: Math.round(height) }};
        }}

        function updatePreview() {{
            if (!img.complete) return;

            try {{
                const outSize = getOutputSize();
                const outputW = outSize.w;
                const outputH = outSize.h;

                // 프리뷰 캔버스 = 출력 크기 그대로
                previewCanvas.width = outputW;
                previewCanvas.height = outputH;
                previewSize.textContent = `${{outputW}} x ${{outputH}}`;

                // src: 원본 이미지의 4점, dst: 출력 이미지의 4점
                const H = computeHomography(
                    [{{x:0,y:0}}, {{x:outputW,y:0}}, {{x:outputW,y:outputH}}, {{x:0,y:outputH}}],
                    points
                );

                // 원본 이미지 캔버스에서 데이터 가져오기 (오버레이 없음)
                const srcData = imgCtx.getImageData(0, 0, imgCanvas.width, imgCanvas.height);

                // 출력 크기로 직접 렌더링
                const dstData = previewCtx.createImageData(outputW, outputH);

                for (let py = 0; py < outputH; py++) {{
                    for (let px = 0; px < outputW; px++) {{
                        const src = applyHomography(H, px, py);
                        const sx = Math.round(src.x);
                        const sy = Math.round(src.y);

                        if (sx >= 0 && sx < imgCanvas.width && sy >= 0 && sy < imgCanvas.height) {{
                            const srcIdx = (sy * imgCanvas.width + sx) * 4;
                            const dstIdx = (py * outputW + px) * 4;
                            dstData.data[dstIdx] = srcData.data[srcIdx];
                            dstData.data[dstIdx+1] = srcData.data[srcIdx+1];
                            dstData.data[dstIdx+2] = srcData.data[srcIdx+2];
                            dstData.data[dstIdx+3] = 255;
                        }}
                    }}
                }}

                previewCtx.putImageData(dstData, 0, 0);
            }} catch(e) {{
                console.error('Preview error:', e);
                previewCtx.fillStyle = '#ffcccc';
                previewCtx.fillRect(0, 0, previewCanvas.width, previewCanvas.height);
                previewCtx.fillStyle = '#cc0000';
                previewCtx.font = '14px Arial';
                previewCtx.fillText('Error: ' + e.message, 10, 30);
            }}
        }}

        function updateCoords() {{
            const labels = ['TL', 'TR', 'BR', 'BL'];
            let html = '';
            points.forEach((p, i) => {{
                const realX = Math.round(p.x / scale);
                const realY = Math.round(p.y / scale);
                html += `<span style="margin-right: 12px;">${{labels[i]}}: (${{realX}}, ${{realY}})</span>`;
            }});
            coordsDisplay.innerHTML = html;

            const realPoints = points.map(p => ({{
                x: Math.round(p.x / scale),
                y: Math.round(p.y / scale)
            }}));
            pointsDataInput.value = JSON.stringify(realPoints);
        }}

        function getMousePos(e) {{
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            return {{
                x: (e.clientX - rect.left) * scaleX,
                y: (e.clientY - rect.top) * scaleY
            }};
        }}

        function findPoint(pos) {{
            for (let i = 0; i < points.length; i++) {{
                const dx = pos.x - points[i].x;
                const dy = pos.y - points[i].y;
                if (Math.sqrt(dx*dx + dy*dy) < pointRadius * 2.5) {{
                    return i;
                }}
            }}
            return -1;
        }}

        canvas.addEventListener('mousedown', (e) => {{
            const pos = getMousePos(e);
            draggingPoint = findPoint(pos);
            if (draggingPoint >= 0) {{
                canvas.style.cursor = 'grabbing';
            }}
        }});

        canvas.addEventListener('mousemove', (e) => {{
            const pos = getMousePos(e);
            if (draggingPoint >= 0) {{
                points[draggingPoint].x = Math.max(0, Math.min(canvas.width, pos.x));
                points[draggingPoint].y = Math.max(0, Math.min(canvas.height, pos.y));
                draw();
                updatePreview();
            }} else {{
                canvas.style.cursor = findPoint(pos) >= 0 ? 'grab' : 'crosshair';
            }}
        }});

        canvas.addEventListener('mouseup', () => {{
            draggingPoint = -1;
            canvas.style.cursor = 'crosshair';
        }});

        // 캔버스 밖에서도 드래그 유지
        document.addEventListener('mousemove', (e) => {{
            if (draggingPoint >= 0) {{
                const rect = canvas.getBoundingClientRect();
                const scaleX = canvas.width / rect.width;
                const scaleY = canvas.height / rect.height;
                const x = (e.clientX - rect.left) * scaleX;
                const y = (e.clientY - rect.top) * scaleY;
                points[draggingPoint].x = Math.max(0, Math.min(canvas.width, x));
                points[draggingPoint].y = Math.max(0, Math.min(canvas.height, y));
                draw();
                updatePreview();
            }}
        }});

        document.addEventListener('mouseup', () => {{
            if (draggingPoint >= 0) {{
                draggingPoint = -1;
                canvas.style.cursor = 'crosshair';
            }}
        }});

        // 리셋 버튼
        resetBtn.addEventListener('click', () => {{
            points = initialPoints.map(p => ({{...p}}));
            draw();
            updatePreview();
        }});

        // 다운로드 버튼 - 고해상도 이미지 생성
        const downloadBtn = document.getElementById('downloadBtn');
        const downloadStatus = document.getElementById('downloadStatus');

        downloadBtn.addEventListener('click', () => {{
            if (!img.complete) return;

            try {{
                // fullScale 기준으로 출력 크기 계산
                const realPts = points.map(p => ({{x: p.x / fullScale, y: p.y / fullScale}}));
                const outputW = Math.round(Math.max(
                    Math.sqrt(Math.pow(realPts[1].x - realPts[0].x, 2) + Math.pow(realPts[1].y - realPts[0].y, 2)),
                    Math.sqrt(Math.pow(realPts[2].x - realPts[3].x, 2) + Math.pow(realPts[2].y - realPts[3].y, 2))
                ));
                const outputH = Math.round(Math.max(
                    Math.sqrt(Math.pow(realPts[3].x - realPts[0].x, 2) + Math.pow(realPts[3].y - realPts[0].y, 2)),
                    Math.sqrt(Math.pow(realPts[2].x - realPts[1].x, 2) + Math.pow(realPts[2].y - realPts[1].y, 2))
                ));

                // 고해상도 출력용 캔버스 생성
                const hiResCanvas = document.createElement('canvas');
                hiResCanvas.width = outputW;
                hiResCanvas.height = outputH;
                const hiResCtx = hiResCanvas.getContext('2d');

                // 원본 이미지를 실제 크기로 로드
                const fullImg = new Image();
                fullImg.onload = function() {{
                    // 풀사이즈 이미지 캔버스
                    const fullCanvas = document.createElement('canvas');
                    fullCanvas.width = fullImg.width;
                    fullCanvas.height = fullImg.height;
                    const fullCtx = fullCanvas.getContext('2d');
                    fullCtx.drawImage(fullImg, 0, 0);

                    // 호모그래피 계산 (실제 좌표 기준)
                    const H = computeHomography(
                        [{{x:0,y:0}}, {{x:outputW,y:0}}, {{x:outputW,y:outputH}}, {{x:0,y:outputH}}],
                        realPts
                    );

                    const srcData = fullCtx.getImageData(0, 0, fullImg.width, fullImg.height);
                    const dstData = hiResCtx.createImageData(outputW, outputH);

                    for (let py = 0; py < outputH; py++) {{
                        for (let px = 0; px < outputW; px++) {{
                            const src = applyHomography(H, px, py);
                            const sx = Math.round(src.x);
                            const sy = Math.round(src.y);

                            if (sx >= 0 && sx < fullImg.width && sy >= 0 && sy < fullImg.height) {{
                                const srcIdx = (sy * fullImg.width + sx) * 4;
                                const dstIdx = (py * outputW + px) * 4;
                                dstData.data[dstIdx] = srcData.data[srcIdx];
                                dstData.data[dstIdx+1] = srcData.data[srcIdx+1];
                                dstData.data[dstIdx+2] = srcData.data[srcIdx+2];
                                dstData.data[dstIdx+3] = 255;
                            }}
                        }}
                    }}

                    hiResCtx.putImageData(dstData, 0, 0);

                    // 다운로드
                    const link = document.createElement('a');
                    link.download = 'transformed_' + outputW + 'x' + outputH + '.png';
                    link.href = hiResCanvas.toDataURL('image/png');
                    link.click();

                    downloadStatus.textContent = 'Done!';
                    setTimeout(() => {{ downloadStatus.textContent = ''; }}, 2000);
                }};

                // 원본 이미지 URL에서 풀사이즈 로드
                fullImg.src = '{full_img_base64}';
            }} catch(e) {{
                console.error('Download error:', e);
                downloadStatus.textContent = 'Error: ' + e.message;
            }}
        }});

        draw();
    }})();
    </script>
    """


def perspective_transform_page():
    st.title("원근변환 크롭")

    uploaded_file = st.file_uploader("이미지 업로드", type=['png', 'jpg', 'jpeg'])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        img_array = np.array(image)

        # 이미지 크기 조정 (캔버스용)
        max_width = 600
        scale = 1.0
        if image.width > max_width:
            scale = max_width / image.width
            display_width = max_width
            display_height = int(image.height * scale)
        else:
            display_width = image.width
            display_height = image.height

        # 리사이즈된 이미지를 base64로 변환 (디스플레이용)
        img_resized = image.resize((display_width, display_height))
        buffered = io.BytesIO()
        img_resized.save(buffered, format="PNG")
        img_base64 = "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode()

        # 원본 이미지 (고해상도 다운로드용, 최대 4000px 제한)
        max_full_size = 4000
        if max(image.width, image.height) > max_full_size:
            ratio = max_full_size / max(image.width, image.height)
            full_image = image.resize((int(image.width * ratio), int(image.height * ratio)), Image.LANCZOS)
        else:
            full_image = image

        full_buffered = io.BytesIO()
        full_image.save(full_buffered, format="PNG")
        full_img_base64 = "data:image/png;base64," + base64.b64encode(full_buffered.getvalue()).decode()

        # full_image 기준 스케일 계산
        full_scale = display_width / full_image.width

        # 커스텀 HTML 캔버스 (프리뷰 포함)
        html_content = get_perspective_canvas_html(
            img_base64, full_img_base64,
            display_width, display_height, scale, full_scale
        )
        # 반응형이므로 충분한 높이 확보
        components.html(html_content, height=1000)


def get_inpaint_canvas_html(img_base64, width, height, brush_size):
    """인페인트용 마스킹 캔버스 HTML/JS"""
    return f"""
    <div>
        <canvas id="inpaintCanvas" width="{width}" height="{height}"
                style="border: 1px solid #ccc; cursor: crosshair;"></canvas>
        <div style="margin-top: 10px;">
            <button id="clearBtn" style="padding: 5px 15px; margin-right: 10px;">지우기</button>
            <span id="maskStatus">마스크: 준비됨</span>
        </div>
        <input type="hidden" id="maskData" value="">
    </div>

    <script>
    (function() {{
        const canvas = document.getElementById('inpaintCanvas');
        const ctx = canvas.getContext('2d');
        const clearBtn = document.getElementById('clearBtn');
        const maskStatus = document.getElementById('maskStatus');
        const maskDataInput = document.getElementById('maskData');

        let img = new Image();
        let isDrawing = false;
        const brushSize = {brush_size};

        // 마스크 레이어
        const maskCanvas = document.createElement('canvas');
        maskCanvas.width = canvas.width;
        maskCanvas.height = canvas.height;
        const maskCtx = maskCanvas.getContext('2d');

        img.onload = function() {{
            draw();
        }};
        img.src = '{img_base64}';

        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

            // 마스크 오버레이 (반투명 빨간색)
            ctx.globalAlpha = 0.5;
            ctx.drawImage(maskCanvas, 0, 0);
            ctx.globalAlpha = 1.0;
        }}

        function updateMaskData() {{
            maskDataInput.value = maskCanvas.toDataURL('image/png');
        }}

        canvas.addEventListener('mousedown', (e) => {{
            isDrawing = true;
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            maskCtx.fillStyle = '#ff0000';
            maskCtx.beginPath();
            maskCtx.arc(x, y, brushSize/2, 0, Math.PI * 2);
            maskCtx.fill();
            draw();
        }});

        canvas.addEventListener('mousemove', (e) => {{
            if (!isDrawing) return;
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            maskCtx.fillStyle = '#ff0000';
            maskCtx.beginPath();
            maskCtx.arc(x, y, brushSize/2, 0, Math.PI * 2);
            maskCtx.fill();
            draw();
        }});

        canvas.addEventListener('mouseup', () => {{
            isDrawing = false;
            updateMaskData();
            maskStatus.textContent = '마스크: 업데이트됨 ✓';
        }});

        canvas.addEventListener('mouseleave', () => {{
            if (isDrawing) {{
                isDrawing = false;
                updateMaskData();
            }}
        }});

        clearBtn.addEventListener('click', () => {{
            maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
            draw();
            maskDataInput.value = '';
            maskStatus.textContent = '마스크: 초기화됨';
        }});

        draw();
    }})();
    </script>
    """


def inpaint_page():
    st.title("인페인트")
    st.markdown("브러시로 제거할 영역을 칠하세요")

    @st.cache_resource
    def load_lama():
        from simple_lama_inpainting import SimpleLama
        return SimpleLama(device='mps')

    # 이미지 소스 선택
    source = st.radio("이미지 소스", ["파일 업로드", "원근변환 결과 사용"], horizontal=True)

    img_array = None
    if source == "파일 업로드":
        uploaded_file = st.file_uploader("이미지 업로드", type=['png', 'jpg', 'jpeg'], key="inpaint_upload")
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            img_array = np.array(image)
    else:
        if st.session_state.transformed_image is not None:
            img_array = st.session_state.transformed_image
        else:
            st.warning("원근변환 결과가 없습니다. 먼저 원근변환을 수행하세요.")

    if img_array is not None:
        col1, col2 = st.columns(2)

        with col1:
            brush_size = st.slider("브러시 크기", 5, 100, 30)

            # 캔버스 크기 계산
            max_width = 600
            h, w = img_array.shape[:2]
            if w > max_width:
                scale = max_width / w
                canvas_w = max_width
                canvas_h = int(h * scale)
            else:
                scale = 1.0
                canvas_w = w
                canvas_h = h

            # 이미지를 base64로 변환
            img_pil = Image.fromarray(img_array).resize((canvas_w, canvas_h))
            buffered = io.BytesIO()
            img_pil.save(buffered, format="PNG")
            img_base64 = "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode()

            st.subheader("마스킹 영역 그리기")
            html_content = get_inpaint_canvas_html(img_base64, canvas_w, canvas_h, brush_size)
            components.html(html_content, height=canvas_h + 60)

            # 마스크 데이터 입력
            mask_data = st.text_input("마스크 데이터 (자동)", key="mask_input", label_visibility="collapsed")

        with col2:
            st.subheader("결과")

            if st.button("🎨 인페인팅 실행", type="primary", use_container_width=True):
                with st.spinner("인페인팅 처리 중..."):
                    lama = load_lama()

                    # RGB 확인
                    if len(img_array.shape) == 2:
                        img_rgb = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
                    elif img_array.shape[2] == 4:
                        img_rgb = img_array[:, :, :3]
                    else:
                        img_rgb = img_array

                    # 마스크 생성 (전체 이미지의 중앙 영역을 예시로)
                    # 실제로는 mask_data에서 가져와야 하지만, JS→Python 통신 한계로 간단한 마스크 사용
                    h, w = img_rgb.shape[:2]
                    mask = np.zeros((h, w), dtype=np.uint8)

                    # 임시: 사용자가 수동으로 마스크 영역 지정
                    st.info("💡 현재 버전에서는 Gradio 앱(app.py)의 인페인트 기능을 사용하세요.")

            if 'inpaint_result' in st.session_state and st.session_state.inpaint_result is not None:
                st.image(st.session_state.inpaint_result, caption="인페인트 결과", use_column_width=True)


# 페이지 라우팅
if page == "원근변환 크롭":
    perspective_transform_page()
elif page == "인페인트":
    inpaint_page()
