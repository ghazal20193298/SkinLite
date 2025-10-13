# SkinLite  
OpenCV 기반 피부 상태 간이 진단 오픈소스 프로그램  
학번: 20193298 / 이름: 가잘  

---

## 1. 프로젝트 개요  
SkinLite는 사용자의 얼굴 이미지를 입력받아  
피부의 붉은기(Redness), 반점(Blemish), 피부 톤 균일도(Tone Uniformity)를  
시각적으로 분석하는 오픈소스 기반 진단 프로그램입니다.  

AI 모델을 사용하지 않고, OpenCV 색상 공간 분석(HSV, YCrCb)을 이용하여  
빠르게 결과를 제공하며, 개인정보를 서버에 업로드하지 않아  
로컬 환경에서도 안전하게 사용할 수 있습니다.

---

## 2. 주요 기능  
- 얼굴 자동 인식 (Haar Cascade 기반)  
- HSV 및 YCrCb 색공간을 활용한 피부 영역 추출  
- 붉은기, 반점, 톤 균일도 지표 계산  
- GUI를 통한 시각화 및 결과 이미지 저장  

---

## 3. 개발 환경  
| 항목 | 내용 |
|------|------|
| 언어 | Python 3.10 |
| 주요 라이브러리 | OpenCV, NumPy, PyQt5 |
| 운영체제 | macOS / Ubuntu |

---

## 4. 실행 방법  
```bash
pip install -r requirements.txt  
python gui_main.py
