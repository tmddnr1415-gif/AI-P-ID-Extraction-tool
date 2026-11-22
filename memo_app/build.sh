#!/bin/sh
# 메모장.exe 만들기 (리눅스에서 Windows 실행 파일 · 시험용 리눅스 파일)
#   sh memo_app/build.sh   → dist/memo_app/메모장.exe , memo_app/out/memo_linux (시험용, 커밋 안 함)
set -e
cd "$(dirname "$0")"
R=..
rm -rf web && mkdir -p web/apps/pdfjs web/apps/translate
cp $R/dashboard/dashboard.html web/dashboard.html
cp -r $R/dashboard/apps/pdfjs/. web/apps/pdfjs/
cp -r $R/dashboard/apps/translate/ocr web/apps/translate/ocr
cp $R/dashboard/apps/translate/README.txt web/apps/translate/README.txt
mkdir -p web/apps/fonts && cp -r $R/dashboard/apps/fonts/pretendard web/apps/fonts/pretendard   # 2026-11-22 Pretendard 글꼴
mkdir -p $R/dist/memo_app out
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -buildvcs=false -ldflags "-s -w -H=windowsgui -buildid=" -o "$R/dist/memo_app/메모장.exe" .
CGO_ENABLED=0 go build -trimpath -buildvcs=false -ldflags "-buildid=" -o out/memo_linux .
ls -l "$R/dist/memo_app/메모장.exe" out/memo_linux
