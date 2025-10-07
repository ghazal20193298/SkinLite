# app.py — skin-light core analysis (v3, 2025-10)
import os, json
import cv2, numpy as np

# ---------- Utils ----------
def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def read_image(path: str):
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(
            f"이미지를 불러올 수 없습니다: {path}\n"
            f"- 경로/파일명 확인\n- HEIC은 지원 X (JPG/PNG 권장)"
        )
    return img

def detect_face_bbox(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
    if len(faces) == 0:
        h, w = img.shape[:2]
        return (int(w*0.1), int(h*0.1), int(w*0.8), int(h*0.8))  # fallback: 중앙영역
    # 가장 큰 얼굴
    x, y, w, h = sorted(faces, key=lambda r: r[2]*r[3], reverse=True)[0]
    return (x, y, w, h)

def apply_light_compensation(bgr):
    # Y(밝기) 채널 CLAHE
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycrcb)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    y2 = clahe.apply(y)
    out = cv2.cvtColor(cv2.merge([y2, cr, cb]), cv2.COLOR_YCrCb2BGR)
    return out

def get_skin_mask(bgr):
    """HSV + YCrCb 결합 마스크 (조명/색차에 비교적 강함)"""
    img = bgr.copy()
    img_blur = cv2.bilateralFilter(img, 7, 50, 50)

    hsv = cv2.cvtColor(img_blur, cv2.COLOR_BGR2HSV)
    ycc = cv2.cvtColor(img_blur, cv2.COLOR_BGR2YCrCb)

    # HSV 범위 (피부톤 근사)
    lower_hsv = np.array([0, 30, 30], dtype=np.uint8)
    upper_hsv = np.array([25, 180, 255], dtype=np.uint8)
    mask_hsv = cv2.inRange(hsv, lower_hsv, upper_hsv)

    # YCrCb 범위 (피부톤 근사)
    lower_ycc = np.array([0, 135, 85], dtype=np.uint8)
    upper_ycc = np.array([255, 180, 135], dtype=np.uint8)
    mask_ycc = cv2.inRange(ycc, lower_ycc, upper_ycc)

    mask = cv2.bitwise_and(mask_hsv, mask_ycc)

    # 모폴로지 정리
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)

    # 얼굴 외부 제거를 위해 컨벡스헐 보정(옵션)
    return mask

def compute_indices(bgr, mask):
    """세 지표 계산: Redness, Blemish, Tone Uniformity (0~1 스케일)"""
    # 붉은기: (R - G)+ 평균
    b, g, r = cv2.split(bgr)
    red_map = cv2.subtract(r, g)  # R-G
    red_map = cv2.max(red_map, 0)
    m = (mask > 0)
    if m.sum() < 50:  # 마스크가 너무 작으면 전체 사용
        m = np.ones_like(red_map, dtype=bool)

    redness = float(red_map[m].mean() / 255.0)
    redness = float(np.clip(redness, 0.0, 1.0))

    # 반점(Blemish): Laplacian 변동성 (텍스처 강도)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_32F, ksize=3)
    # 마스크 영역의 표준편차 → 0~1 정규화
    std = float(lap[m].std())
    blemish = float(np.clip(std / 40.0, 0.0, 1.0))  # 경험적 스케일

    # 톤 균일(Uniformity): 밝기(Y) 표준편차 → 1 - 정규화
    ycc = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    y = ycc[...,0].astype(np.float32)
    tone_std = float(y[m].std())
    tone = float(1.0 - np.clip(tone_std / 64.0, 0.0, 1.0))  # std 작을수록 균일

    return redness, blemish, tone, red_map

def visualize(bgr, mask, red_map, scores):
    """히트맵 오버레이 + 게이지 바"""
    redness, blemish, tone = scores
    # 히트맵: redness를 컬러맵으로
    heat = cv2.normalize(red_map, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    heat = cv2.applyColorMap(heat, cv2.COLORMAP_JET)
    heat[mask == 0] = 0
    overlay = cv2.addWeighted(bgr, 0.7, heat, 0.6, 0)

    # 게이지 바 렌더링(아래쪽)
    h, w = overlay.shape[:2]
    panel_h = 80
    canvas = np.full((h + panel_h, w, 3), 255, np.uint8)
    canvas[:h] = overlay

    def draw_gauge(x, label, val):
        y0 = h + 20
        w_bar, h_bar = int(w*0.28), 14
        cv2.putText(canvas, f"{label}: {val:.2f}", (x, y0-6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60,60,60), 1, cv2.LINE_AA)
        cv2.rectangle(canvas, (x, y0+10), (x+w_bar, y0+10+h_bar), (210,210,210), -1)
        cv2.rectangle(canvas, (x, y0+10), (x+int(w_bar*val), y0+10+h_bar), (50,120,255), -1)
        cv2.rectangle(canvas, (x, y0+10), (x+w_bar, y0+10+h_bar), (90,90,90), 1)

    gap = int(w*0.08)
    start = int(w*0.06)
    draw_gauge(start + (w//3)*0, "Redness", redness)
    draw_gauge(start + (w//3)*1, "Blemish", blemish)
    draw_gauge(start + (w//3)*2, "Tone", tone)

    # 요약 문장
    txt = []
    txt.append("홍조 " + ("↑높음" if redness >= 0.6 else "보통" if redness >= 0.3 else "낮음"))
    txt.append("반점/요철 " + ("↑뚜렷" if blemish >= 0.6 else "보통" if blemish >= 0.3 else "미약"))
    txt.append("톤 균일 " + ("좋음" if tone >= 0.6 else "보통" if tone >= 0.3 else "불균일"))
    summary = " · ".join(txt)
    cv2.putText(canvas, summary, (start, h + 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30,30,30), 2, cv2.LINE_AA)

    return canvas

# ---------- Public API ----------
def analyze(
    image_path: str,
    save_path: str = "outputs/result.png",
    *,
    auto_face: bool = True,
    light_comp: bool = False,
    export_json: str | None = None,
    return_image: bool = False,
):
    """Returns:
      - 기본: (redness, blemish, tone, save_path)
      - return_image=True: (redness, blemish, tone, save_path, vis_img)
    """
    _ensure_dir(save_path)
    img = read_image(image_path)

    # 얼굴 박스 → 피부 마스크 범위를 얼굴 근처로 제한(과도한 배경 제거)
    if auto_face:
        x, y, w, h = detect_face_bbox(img)
        face_roi = img[y:y+h, x:x+w].copy()
    else:
        face_roi = img.copy()

    if light_comp:
        face_roi = apply_light_compensation(face_roi)

    mask = get_skin_mask(face_roi)
    r, b, t, red_map = compute_indices(face_roi, mask)
    vis = visualize(face_roi, mask, red_map, (r, b, t))

    cv2.imwrite(save_path, vis)

    if export_json:
        _ensure_dir(export_json)
        with open(export_json, "w", encoding="utf-8") as f:
            json.dump(
                {"redness": round(r,3), "blemish": round(b,3), "tone_uniformity": round(t,3),
                 "image": image_path, "result_image": save_path,
                 "auto_face": auto_face, "light_comp": light_comp},
                f, ensure_ascii=False, indent=2
            )

    if return_image:
        return r, b, t, save_path, vis
    return r, b, t, save_path

if __name__ == "__main__":
    # 빠른 CLI 사용 예:
    # python app.py "face.jpg"
    import sys
    if len(sys.argv) < 2:
        print("Usage: python app.py <image_path>")
        sys.exit(1)
    _, img_path = sys.argv[:2]
    r, b, t, out = analyze(img_path, "outputs/result.png", auto_face=True, light_comp=True)
    print(f"Redness={r:.3f}, Blemish={b:.3f}, Tone={t:.3f}\nSaved → {out}")
