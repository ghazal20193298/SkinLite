# gui_main.py — Skin-Light 최종 GUI
import os, sys, cv2
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QFileDialog, QVBoxLayout, QHBoxLayout, QProgressBar,
    QStatusBar, QCheckBox, QMessageBox
)
from PyQt5.QtGui import QPixmap, QImage, QFont
from PyQt5.QtCore import Qt
from app import analyze  # app.py 불러오기

APP_TITLE = "SkinLite — 피부 분석 오픈소스 앱"

def cv2_to_pixmap(bgr):
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    img = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
    return QPixmap.fromImage(img)

class SkinLightApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(960, 600)
        self.image_path = None
        self.result_img = None
        self.result_scores = None

        # --- UI 구성 ---
        title = QLabel("✨ SkinLite")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 20, QFont.Bold))
        subtitle = QLabel("색공간 기반 피부 간이 진단")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: gray;")

        self.src_label = QLabel("원본 이미지")
        self.src_label.setAlignment(Qt.AlignCenter)
        self.src_label.setStyleSheet("border:1px solid #ccc; background:#fafafa;")

        self.out_label = QLabel("결과 이미지")
        self.out_label.setAlignment(Qt.AlignCenter)
        self.out_label.setStyleSheet("border:1px solid #ccc; background:#fafafa;")

        self.pb_red = QProgressBar(); self.pb_red.setFormat("Redness: %p%")
        self.pb_ble = QProgressBar(); self.pb_ble.setFormat("Blemish: %p%")
        self.pb_ton = QProgressBar(); self.pb_ton.setFormat("Tone: %p%")

        self.cb_face = QCheckBox("자동 얼굴 감지"); self.cb_face.setChecked(True)
        self.cb_light = QCheckBox("조명 보정(CLAHE)"); self.cb_light.setChecked(True)

        btn_open = QPushButton("이미지 불러오기")
        btn_run = QPushButton("분석 실행")
        btn_save = QPushButton("결과 저장")
        btn_json = QPushButton("JSON 내보내기")
        btn_reset = QPushButton("초기화")

        btn_open.clicked.connect(self.open_image)
        btn_run.clicked.connect(self.run_analysis)
        btn_save.clicked.connect(self.save_result)
        btn_json.clicked.connect(self.export_json)
        btn_reset.clicked.connect(self.reset)

        layout_main = QVBoxLayout()
        layout_top = QVBoxLayout(); layout_top.addWidget(title); layout_top.addWidget(subtitle)
        layout_preview = QHBoxLayout(); layout_preview.addWidget(self.src_label); layout_preview.addWidget(self.out_label)
        layout_bars = QHBoxLayout(); layout_bars.addWidget(self.pb_red); layout_bars.addWidget(self.pb_ble); layout_bars.addWidget(self.pb_ton)
        layout_opts = QHBoxLayout(); layout_opts.addWidget(self.cb_face); layout_opts.addWidget(self.cb_light)
        layout_btns = QHBoxLayout(); layout_btns.addWidget(btn_open); layout_btns.addWidget(btn_run); layout_btns.addWidget(btn_save); layout_btns.addWidget(btn_json); layout_btns.addWidget(btn_reset)

        layout_main.addLayout(layout_top)
        layout_main.addLayout(layout_preview)
        layout_main.addLayout(layout_bars)
        layout_main.addLayout(layout_opts)
        layout_main.addLayout(layout_btns)

        container = QWidget(); container.setLayout(layout_main)
        self.setCentralWidget(container)
        self.setStatusBar(QStatusBar())

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "이미지 선택", "", "Images (*.jpg *.jpeg *.png)")
        if not path: return
        self.image_path = path
        bgr = cv2.imread(path)
        if bgr is None:
            QMessageBox.warning(self, "오류", "이미지를 열 수 없습니다.")
            return
        pix = cv2_to_pixmap(bgr)
        self.src_label.setPixmap(pix.scaled(self.src_label.width(), self.src_label.height(), Qt.KeepAspectRatio))
        self.statusBar().showMessage(f"불러온 파일: {os.path.basename(path)}")

    def run_analysis(self):
        if not self.image_path:
            QMessageBox.information(self, "안내", "이미지를 먼저 불러와 주세요.")
            return
        r, b, t, save_path, vis = analyze(
            self.image_path,
            save_path="outputs/result.png",
            auto_face=self.cb_face.isChecked(),
            light_comp=self.cb_light.isChecked(),
            return_image=True
        )
        self.result_img = vis
        self.result_scores = (r, b, t)
        pix = cv2_to_pixmap(vis)
        self.out_label.setPixmap(pix.scaled(self.out_label.width(), self.out_label.height(), Qt.KeepAspectRatio))
        self.pb_red.setValue(int(r * 100))
        self.pb_ble.setValue(int(b * 100))
        self.pb_ton.setValue(int(t * 100))
        self.statusBar().showMessage(f"분석 완료: Red={r:.2f}, Blem={b:.2f}, Tone={t:.2f}")

    def save_result(self):
        if self.result_img is None:
            QMessageBox.information(self, "안내", "먼저 분석을 실행해 주세요.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "결과 저장", "result.png", "Images (*.png)")
        if not path: return
        cv2.imwrite(path, self.result_img)
        self.statusBar().showMessage(f"결과 저장 완료: {path}")

    def export_json(self):
        if not self.image_path:
            QMessageBox.information(self, "안내", "이미지를 먼저 분석하세요.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "JSON 저장", "metrics.json", "JSON (*.json)")
        if not path: return
        analyze(
            self.image_path, "outputs/result.png",
            auto_face=self.cb_face.isChecked(),
            light_comp=self.cb_light.isChecked(),
            export_json=path
        )
        self.statusBar().showMessage(f"JSON 저장 완료: {path}")

    def reset(self):
        self.image_path = None
        self.result_img = None
        self.result_scores = None
        self.src_label.clear(); self.src_label.setText("원본 이미지")
        self.out_label.clear(); self.out_label.setText("결과 이미지")
        self.pb_red.setValue(0); self.pb_ble.setValue(0); self.pb_ton.setValue(0)
        self.statusBar().clearMessage()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SkinLightApp()
    w.show()
    sys.exit(app.exec_())
