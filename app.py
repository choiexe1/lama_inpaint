import gradio as gr
import numpy as np
from PIL import Image
from simple_lama_inpainting import SimpleLama

lama = SimpleLama(device='mps')

def inpaint(image_data):
    if image_data is None:
        return None

    background = image_data["background"]
    layers = image_data["layers"]

    if background is None or len(layers) == 0:
        return None

    # 배경 이미지 (RGB로 변환)
    if isinstance(background, np.ndarray):
        img = background
    else:
        img = np.array(background)

    # RGBA -> RGB 변환
    if img.shape[-1] == 4:
        img = img[:, :, :3]

    # 마스크 추출 (알파 채널)
    mask_layer = layers[0]
    if isinstance(mask_layer, np.ndarray):
        mask = mask_layer
    else:
        mask = np.array(mask_layer)

    # 알파 채널에서 마스크 생성
    if mask.shape[-1] == 4:
        mask = mask[:, :, 3]

    # 마스크 이진화
    mask = (mask > 0).astype(np.uint8) * 255

    # 인페인팅 실행
    result = lama(img, mask)

    return result

def update_brush(size):
    return gr.ImageEditor(
        type="numpy",
        label="이미지 편집 (브러시로 마스킹)",
        interactive=True,
        brush=gr.Brush(colors=["#FF0000"], default_size=size),
        eraser=gr.Eraser(default_size=size),
    )

with gr.Blocks(title="LaMa Inpainting") as demo:
    gr.Markdown("## LaMa Inpainting - 드래그로 마스킹")
    gr.Markdown("이미지를 업로드하고, 브러시로 제거할 영역을 칠하세요.")

    brush_size = gr.Slider(minimum=1, maximum=100, value=20, step=1, label="브러시 크기")

    with gr.Row():
        editor = gr.ImageEditor(
            type="numpy",
            label="이미지 편집 (브러시로 마스킹)",
            interactive=True,
            brush=gr.Brush(colors=["#FF0000"], default_size=20),
            eraser=gr.Eraser(default_size=20),
        )
        output = gr.Image(label="결과", type="pil")

    with gr.Row():
        btn = gr.Button("인페인팅 실행", variant="primary")
        save_btn = gr.Button("결과 저장")

    brush_size.change(fn=update_brush, inputs=brush_size, outputs=editor)

    btn.click(fn=inpaint, inputs=editor, outputs=output)
    save_btn.click(
        fn=lambda img: img.save("template.png") if img else None,
        inputs=output,
        outputs=None
    )

if __name__ == "__main__":
    demo.launch()
