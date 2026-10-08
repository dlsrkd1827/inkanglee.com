inkanglee.com (Wix) -> 정적 HTML 변환 도구

1) 원본 데이터 받기
   python -I fetch.py snapshot          (데스크톱. inkanglee.com 이 Wix 에 연결돼 있던 시점에만 가능)
   python -I fetch_mobile.py snapshot_m (모바일. Wix 무료 주소 dlsrkd1827.wixsite.com/leeinkang 에서 받음)
2) HTML 생성 + 이미지/영상 다운로드 (이미 받은 파일은 건너뜀)
   python -I build.py snapshot .. --mobile snapshot_m

주의: build.py 는 사이트 폴더의 *.html 을 덮어씁니다. HTML을 직접 고쳐 쓰기 시작했다면 다시 실행하지 마세요.
