Streamlit 앱 배포 가이드

만드신 Balance Box Simulator를 웹에 배포하여 다른 사람들과 공유하는 방법입니다.

1. 준비물 확인

배포를 위해서는 아래 3개의 파일이 한 폴더에 있어야 합니다.

app.py (메인 실행 파일)

logic.py (알고리즘 로직 파일)

requirements.txt (방금 생성된 라이브러리 목록)

2. GitHub에 업로드

Streamlit Community Cloud는 GitHub 저장소(Repository)의 코드를 가져와서 실행합니다.

GitHub에 로그인합니다.

우측 상단의 + 버튼 -> New repository를 클릭합니다.

저장소 이름(예: balance-box-sim)을 입력하고 Public으로 설정한 뒤 Create repository를 누릅니다.

준비한 3개의 파일을 해당 저장소에 업로드합니다. (Upload files 기능을 사용하거나 git push)

3. Streamlit Community Cloud 배포

Streamlit Community Cloud에 접속하여 GitHub 계정으로 로그인합니다.

New app 버튼을 클릭합니다.

Use existing repo를 선택합니다.

방금 만든 GitHub 저장소, 브랜치(보통 main), 그리고 메인 파일 경로(app.py)를 선택합니다.

Deploy! 버튼을 클릭합니다.

4. 완료

잠시 후 "Your app is in the oven..." 같은 문구가 뜨며 배포가 진행됩니다. 완료되면 전용 URL(예: https://balance-box-sim.streamlit.app)이 생성되며, 이 주소를 다른 사람들에게 공유하면 됩니다.