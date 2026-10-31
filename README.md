# 브랜드 뉴스·검색 추이 분석 대시보드

네이버 API HUB로 수집한 뉴스와 DataLab 검색 추이를 정리하고, 결과를 Streamlit 대시보드로 보여줍니다.

## 구성

| 경로 | 역할 |
|---|---|
| `streamlit_app.py` | 배포 진입점 (대시보드 실행) |
| `analysis/dashboard.py` | 대시보드 본문 |
| `analysis/*.py` | 수집, 정제, 분류, 키워드, 유사도, 검색 추이 스크립트 |
| `data/processed/` | 정제된 분석 입력 (CSV) |
| `data/raw/` | API 원본 응답 (수정하지 않음) |
| `outputs/tables/`, `outputs/figures/` | 표와 그래프 결과 |
| `requirements.txt` | 필요한 패키지 |

대시보드는 `data/processed/`, `outputs/`에 저장된 결과 파일만 읽습니다. API를 새로 호출하지 않으므로 인증값(`api_keys.env`)은 배포에 필요 없습니다.

## 로컬에서 실행

프로젝트 폴더에서 실행합니다.

```bash
py -m pip install -r requirements.txt
```

```bash
py -m streamlit run streamlit_app.py
```

브라우저에서 http://localhost:8501 을 엽니다.

## Streamlit Community Cloud 배포

1. https://share.streamlit.io 에 GitHub 계정으로 로그인합니다.
2. **Create app → Deploy a public app from GitHub**를 선택합니다.
3. 아래 값을 입력합니다.
   - Repository: `blueday-gif/1031-icb16-naverdashboard`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
4. **Deploy**를 누르고 설치가 끝날 때까지 기다립니다.

데이터를 갱신했다면 저장소에 push한 뒤 앱 화면의 **Reboot app**을 누르면 됩니다.

## 주의

- `api_keys.env`와 키 값은 저장소에 올리지 않습니다. `.gitignore`에 등록되어 있습니다.
- 검색 추이 지수는 요청마다 상대 지수입니다. 대시보드의 '해석과 한계' 탭을 함께 보세요.
