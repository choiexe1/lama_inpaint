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

    if isinstance(background, np.ndarray):
        img = background
    else:
        img = np.array(background)

    if img.shape[-1] == 4:
        img = img[:, :, :3]

    mask_layer = layers[0]
    if isinstance(mask_layer, np.ndarray):
        mask = mask_layer
    else:
        mask = np.array(mask_layer)

    if mask.shape[-1] == 4:
        mask = mask[:, :, 3]

    mask = (mask > 0).astype(np.uint8) * 255

    result = lama(img, mask)

    return result

def create_normal_ui():
    with gr.Blocks(title="LaMa Inpainting") as demo:
        gr.Markdown("이미지를 업로드하고, 브러시로 제거할 영역을 칠하세요.")

        brush_size = gr.Slider(minimum=1, maximum=100, value=30, step=1, label="브러시 크기")

        with gr.Row():
            with gr.Column(scale=1):
                editor = gr.ImageEditor(
                    type="numpy",
                    label="이미지 편집 (브러시로 마스킹)",
                    interactive=True,
                    eraser=gr.Eraser(default_size=30),
                    height=700,
                    canvas_size=(1200, 800),
                )
            with gr.Column(scale=1):
                output = gr.Image(label="결과", type="pil", height=700)

        with gr.Row():
            btn = gr.Button("🎨 인페인팅 실행", variant="primary", size="lg")
            save_btn = gr.Button("💾 결과 저장", size="lg")

        def update_brush(size):
            return gr.ImageEditor(
                type="numpy",
                label="이미지 편집 (브러시로 마스킹)",
                interactive=True,
                eraser=gr.Eraser(default_size=size),
                height=700,
                canvas_size=(1200, 800),
            )

        brush_size.change(fn=update_brush, inputs=brush_size, outputs=editor)
        btn.click(fn=inpaint, inputs=editor, outputs=output)
        save_btn.click(
            fn=lambda img: img.save("template.png") if img else None,
            inputs=output,
            outputs=None
        )

    return demo

def create_fullscreen_ui():
    with gr.Blocks(title="LaMa - 전체화면 편집") as demo:

        brush_size = gr.Slider(minimum=1, maximum=150, value=50, step=1, label="브러시 크기")

        editor = gr.ImageEditor(
            type="numpy",
            label="마스킹 영역을 브러시로 칠하세요",
            interactive=True,
            eraser=gr.Eraser(default_size=50),
            height=850,
            canvas_size=(1600, 1000),
        )

        with gr.Row():
            btn = gr.Button("🎨 인페인팅 실행", variant="primary", size="lg")
            save_btn = gr.Button("💾 결과 저장", size="lg")

        output = gr.Image(label="결과", type="pil", height=850)

        def update_brush_fs(size):
            return gr.ImageEditor(
                type="numpy",
                label="마스킹 영역을 브러시로 칠하세요",
                interactive=True,
                eraser=gr.Eraser(default_size=size),
                height=850,
                canvas_size=(1600, 1000),
            )

        brush_size.change(fn=update_brush_fs, inputs=brush_size, outputs=editor)
        btn.click(fn=inpaint, inputs=editor, outputs=output)
        save_btn.click(
            fn=lambda img: img.save("template.png") if img else None,
            inputs=output,
            outputs=None
        )

    return demo

with gr.Blocks(title="LaMa Inpainting") as demo:
    with gr.Tabs():
        with gr.Tab("일반 편집"):
            gr.Markdown("이미지를 업로드하고, 브러시로 제거할 영역을 칠하세요.")

            brush_size = gr.Slider(minimum=1, maximum=100, value=30, step=1, label="브러시 크기")

            with gr.Row():
                with gr.Column(scale=1):
                    editor = gr.ImageEditor(
                        type="numpy",
                        label="이미지 편집 (브러시로 마스킹)",
                        interactive=True,
                        eraser=gr.Eraser(default_size=30),
                        height=600,
                    )
                with gr.Column(scale=1):
                    output = gr.Image(label="결과", type="pil", height=600)

            with gr.Row():
                btn = gr.Button("🎨 인페인팅 실행", variant="primary", size="lg")
                save_btn = gr.Button("💾 결과 저장", size="lg")

            def update_brush(size):
                return gr.ImageEditor(
                    type="numpy",
                    label="이미지 편집 (브러시로 마스킹)",
                    interactive=True,
                    eraser=gr.Eraser(default_size=size),
                    height=600,
                )

            brush_size.change(fn=update_brush, inputs=brush_size, outputs=editor)
            btn.click(fn=inpaint, inputs=editor, outputs=output)
            save_btn.click(
                fn=lambda img: img.save("template.png") if img else None,
                inputs=output,
                outputs=None
            )

        with gr.Tab("🔲 전체화면 편집"):
            gr.Markdown("더 큰 캔버스에서 편하게 마스킹하세요.")

            brush_size_fs = gr.Slider(minimum=1, maximum=150, value=50, step=1, label="브러시 크기")

            editor_fs = gr.ImageEditor(
                type="numpy",
                label="마스킹 영역을 브러시로 칠하세요",
                interactive=True,
                eraser=gr.Eraser(default_size=50),
                height=800,
            )

            with gr.Row():
                btn_fs = gr.Button("🎨 인페인팅 실행", variant="primary", size="lg")
                save_btn_fs = gr.Button("💾 결과 저장", size="lg")

            output_fs = gr.Image(label="결과", type="pil", height=600)

            def update_brush_fs(size):
                return gr.ImageEditor(
                    type="numpy",
                    label="마스킹 영역을 브러시로 칠하세요",
                    interactive=True,
                    eraser=gr.Eraser(default_size=size),
                    height=800,
                )

            brush_size_fs.change(fn=update_brush_fs, inputs=brush_size_fs, outputs=editor_fs)
            btn_fs.click(fn=inpaint, inputs=editor_fs, outputs=output_fs)
            save_btn_fs.click(
                fn=lambda img: img.save("template.png") if img else None,
                inputs=output_fs,
                outputs=None
            )

if __name__ == "__main__":
    demo.launch()
