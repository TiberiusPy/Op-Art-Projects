     @echo off
cd /d C:\Users\Shota\PycharmProjects\PhytonProject
call .venv\Scripts\activate
start http://localhost:8501
streamlit run DesignersPayRoll.py
pause