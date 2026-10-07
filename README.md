# 서울 일별 평균기온 트렌드 분석

2024~2025년 서울의 일별 평균기온을 이용해 시계열 패턴을 분석하는 재현 가능한 프로젝트입니다.

## 실행

Python 3.10 이상에서 아래 명령을 실행합니다.

```bash
python -m pip install -r requirements.txt
python analysis.py
```

포함된 CSV로 그래프와 요약 통계를 다시 만듭니다. 데이터를 다시 내려받으려면 `python analysis.py --refresh`를 실행합니다. 최초 실행 시 CSV가 없으면 Open-Meteo에서 자동 수집합니다.

## 구성

- `analysis.py`: 수집, 정제, 분석, 시각화 코드
- `data/seoul_daily_temperature_2024_2025.csv`: 분석에 사용한 일별 원자료
- `images/`: 리포트에 삽입한 분석 그래프
- `REPORT.md`: 분석 질문, 근거, 해석, 한계 및 AI 사용 로그

## 데이터 출처 및 이용

Open-Meteo Historical Weather API (`https://open-meteo.com/en/docs/historical-weather-api`), 서울 좌표(위도 37.5665, 경도 126.9780), Asia/Seoul 현지 날짜 기준입니다. `temperature_2m_mean`은 재분석 기반 모델 자료이며 관측소의 직접 측정값과 다를 수 있습니다. Open-Meteo 데이터 이용 조건과 출처 표기 요구를 확인하고, 재배포 시 Open-Meteo를 출처로 표시합니다. API 응답과 모델 자료가 갱신되면 새로 수집한 값이 달라질 수 있습니다.