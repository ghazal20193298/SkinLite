# gui_main.py — skin-light main GUI (v3, 2025-10)
import os, sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QProgressBar, QStatusBar, QCheckBox, QMessageBox
)
from PyQt5.QtGui import QPixmap, QImage, QFont
from PyQt5.QtCore import Qt
import cv2
from app import analyze  # v3 analyze

APP_TITLE = "SkinLite — 피부 분석 오픈소스 앱"

def cv2_to_qpixmap(bgr):
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    qimg = QImage(rgb.data, w, h, w*3, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(980, 640)
        self._img_path = None
        self._last_vis = None
        self._last_scores = None
        self._last_save_path = "outputs/result.png"

        title = QLabel("✨ SkinLite")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 20, QFont.Bold))
        subtitle = QLabel("색공간 기반 피부 간이 진단 — 홍조/반점/톤균일")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: gray;")

        # 좌/우 프리뷰
        self.src_view = QLabel("원본")
        self.src_view.setAlignment(Qt.AlignCenter)
        self.src_view.setStyleSheet("border:1px solid #ddd; background:#fafafa;")
        self.out_view = QLabel("결과")
        self.out_view.setAlignment(Qt.AlignCenter)
        self.out_view.setStyleSheet("border:1px solid #ddd; background:#fafafa;")

        # 진행바 3종
        self.pb_red = QProgressBar(); self.pb_red.setFormat("Redness: %p%")
        self.pb_ble = QProgressBar(); self.pb_ble.setFormat("Blemish: %p%")
        self.pb_ton = QProgressBar(); self.pb_ton.setFormat("Tone: %p%")

        # 옵션
        self.cb_face = QCheckBox("자동 얼굴 감지")
        self.cb_face.setChecked(True)
        self.cb_light = QCheckBox("조명 보정(CLAHE)")
        self.cb_light.setChecked(True)

        # 버튼
        btn_open = QPushButton("이미지 열기")
        btn_run  = QPushButton("분석 실행")
        btn_save = QPushButton("결과 저장(PNG)")
        btn_json = QPushButton("지표 내보내기(JSON)")
        btn_reset= QPushButton("초기화")

        btn_open.clicked.connect(self.on_open)
        btn_run.clicked.connect(self.on_run)
        btn_save.clicked.connect(self.on_save)
        btn_json.clicked.connect(self.on_export_json)
        btn_reset.clicked.connect(self.on_reset)

        # Layouts
        top = QVBoxLayout(); top.addWidget(title); top.addWidget(subtitle)
        preview = QHBoxLayout(); preview.addWidget(self.src_view); preview.addWidget(self.out_view)
        bars = QHBoxLayout(); bars.addWidget(self.pb_red); bars.addWidget(self.pb_ble); bars.addWidget(self.pb_ton)
        opts = QHBoxLayout(); opts.addWidget(self.cb_face); opts.addWidget(self.cb_light)
        btns = QHBoxLayout(); btns.addWidget(btn_open); btns.addWidget(btn_run); btns.addWidget(btn_save); btns.addWidget(btn_json); btns.addWidget(btn_reset)

        root = QVBoxLayout()
        root.addLayout(top); root.addSpacing(8)
        root.addLayout(preview, 1)
        root.addSpacing(8); root.addLayout(bars)
        root.addSpacing(4); root.addLayout(opts)
        root.addSpacing(6); root.addLayout(btns)

        central = QWidget(); central.setLayout(root)
        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())

    def on_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "이미지 선택", "", "Images (*.jpg *.jpeg *.png)")
        if not path: return
        self._img_path = path
        bgr = cv2.imread(path)
        if bgr is None:
            QMessageBox.warning(self, "오류", "이미지를 열 수 없습니다.")
            return
        pm = cv2_to_qpixmap(bgr)
        self.src_view.setPixmap(pm.scaled(self.src_view.width(), self.src_view.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.statusBar().showMessage(f"불러온 파일: {os.path.basename(path)}")

    def on_run(self):
        if not self._img_path:
            QMessageBox.information(self, "안내", "이미지를 먼저 열어주세요.")
            return
        r, b, t, save_path, vis = analyze(
            self._img_path, "outputs/result.png",
            auto_face=self.cb_face.isChecked(),
            light_comp=self.cb_light.isChecked(),
            return_image=True
        )
        self._last_vis = vis
        self._last_scores = (r, b, t)
        self._last_save_path = save_path

        # 프리뷰 반영
        pm = cv2_to_qpixmap(vis)
        self.out_view.setPixmap(pm.scaled(self.out_view.width(), self.out_view.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # 진행바(0~100)
        self.pb_red.setValue(int(r*100))
        self.pb_ble.setValue(int(b*100))
        self.pb_ton.setValue(int(t*100))

        self.statusBar().showMessage(f"분석 완료 · Redness={r:.2f}, Blemish={b:.2f}, Tone={t:.2f}")

    def on_save(self):
        if self._last_vis is None:
            QMessageBox.information(self, "안내", "먼저 분석을 실행해 주세요.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "결과 저장", "result.png", "PNG (*.png)")
        if not path: return
        cv2.imwrite(path, self._last_vis)
        self.statusBar().showMessage(f"결과 저장: {path}")

    def on_export_json(self):
        if not self._img_path:
            QMessageBox.information(self, "안내", "먼저 분석을 실행해 주세요.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "JSON 내보내기", "metrics.json", "JSON (*.json)")
        if not path: return
        # analyze에서 export_json 옵션 사용해서 동일 결과 보장
        analyze(
            self._img_path, self._last_save_path,
            auto_face=self.cb_face.isChecked(),
            light_comp=self.cb_light.isChecked(),
            export_json=path,
            return_image=False
        )
        self.statusBar().showMessage(f"지표 JSON 저장: {path}")

    def on_reset(self):
        self._img_path = None
        self._last_vis = None
        self._last_scores = None
        self.src_view.clear(); self.src_view.setText("원본")
        self.out_view.clear(); self.out_view.setText("결과")
        for pb in (self.pb_red, self.pb_ble, self.pb_ton): pb.setValue(0)
        self.statusBar().clearMessage()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow(); w.show()
    sys.exit(app.exec_())
