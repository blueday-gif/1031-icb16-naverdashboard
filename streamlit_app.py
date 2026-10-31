"""Streamlit 배포용 진입점.

Streamlit Community Cloud는 저장소 루트의 streamlit_app.py를 기본 진입점으로 찾는다.
실제 대시보드 코드는 analysis/dashboard.py에 있고, 여기서는 그 파일을 실행만 한다.
로컬 실행: py -m streamlit run streamlit_app.py
"""

import runpy
from pathlib import Path

DASHBOARD = Path(__file__).resolve().parent / "analysis" / "dashboard.py"

runpy.run_path(str(DASHBOARD), run_name="__main__")
