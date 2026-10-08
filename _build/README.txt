inkanglee.com (Wix) -> 정적 HTML 변환 도구

1) 원본 데이터 받기 (페이지 HTML + Wix 페이지 데이터)
   python -I fetch.py snapshot
2) HTML 생성 + 이미지/영상 다운로드 (이미 받은 파일은 건너뜀)
   python -I build.py snapshot ..

주의: build.py 는 사이트 폴더의 *.html 을 덮어씁니다. HTML을 직접 고쳐 쓰기 시작했다면 다시 실행하지 마세요.
