# javis desktop shell

## 목적

이 폴더는 `Python 엔진 + Electron/React UI 셸` 구조의 첫 웹 셸입니다.

## 설치

```powershell
cd "C:\Users\ykim2\Desktop\javis\desktop-shell"
npm install
```

## 개발 실행

터미널 1:

```powershell
cd "C:\Users\ykim2\Desktop\javis"
python -m app.api.server
```

터미널 2:

```powershell
cd "C:\Users\ykim2\Desktop\javis\desktop-shell"
npm run dev:web
```

터미널 3:

```powershell
cd "C:\Users\ykim2\Desktop\javis\desktop-shell"
npm run dev:shell
```

## 빌드

```powershell
cd "C:\Users\ykim2\Desktop\javis\desktop-shell"
npm run build
npm run start
```
