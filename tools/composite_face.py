import cv2
import numpy as np
from pathlib import Path

def composite_face(template_path, face_path, output_path, face_bbox=None):
    template = cv2.imread(str(template_path))
    face = cv2.imread(str(face_path))

    if template is None or face is None:
        raise ValueError("Could not read images")

    if face_bbox is None:
        gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) > 0:
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            face_bbox = (x, y, w, h)
            print(f"Auto-detected face region: {face_bbox}")
        else:
            raise ValueError("Could not detect face. Please provide face_bbox")

    x, y, w, h = face_bbox

    img_h, img_w = template.shape[:2]
    x = max(0, x)
    y = max(0, y)
    w = min(w, img_w - x)
    h = min(h, img_h - y)

    print(f"Using face region: x={x}, y={y}, w={w}, h={h}")
    print(f"Template size: {img_w}x{img_h}")

    face_resized = cv2.resize(face, (w, h))

    result = template.copy()

    result[y:y+h, x:x+w] = face_resized

    cv2.imwrite(str(output_path), result)
    print(f"Saved composited image to {output_path}")

    return result

if __name__ == "__main__":
    template_path = Path("id_template_09.png")
    face_path = Path("a.jpeg")
    output_path = Path("composited_id.png")

    composite_face(template_path, face_path, output_path, face_bbox=(375, 62, 165, 195))
