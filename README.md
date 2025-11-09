# 🎯 GitHub 협업 가이드 (팀 프로젝트용)

## 📍 1️⃣ Git 설치 & 계정 준비
1. [https://git-scm.com/downloads](https://git-scm.com/downloads) 에서 Git 설치  
2. GitHub 계정 가입 후 로그인  
3. 터미널(PowerShell) 실행

---

## 🔐 2️⃣ GitHub 토큰 발급 (처음 push할 때 필요)
1. GitHub → **Settings → Developer settings → Personal access tokens → Tokens (classic)**  
2. **Generate new token (classic)** 클릭  
3. ✅ `repo` 하나만 체크  
4. 만료기간(Expiration): 30~90일  
5. 생성 후 **토큰 복사** (한 번만 볼 수 있음)  

> ⚠️ 절대 코드나 `.env`에 넣지 말고 로그인 창에만 사용!

---

## 💾 3️⃣ 프로젝트 클론 (내 컴퓨터에 복제)
```bash
git clone https://github.com/hazelJung/mini_project_3rd.git
cd mini_project_3rd
```
> Public 저장소는 로그인 없이 바로 가능,  
> Private은 초대 수락 후 토큰 입력 필요.

---

## ⚙️ 4️⃣ 첫 설정 (최초 1회)
```bash
git config --global user.name "본인 이름"
git config --global user.email "깃허브 이메일"
```

---

## 🧩 5️⃣ 기본 Git 명령어 요약

| 명령어 | 설명 |
|--------|------|
| `git status` | 현재 변경된 파일 상태 확인 |
| `git add .` | 수정한 파일을 커밋 준비 상태로 올리기 |
| `git commit -m "메시지"` | 변경사항을 로컬 버전으로 저장 |
| `git pull origin main` | 원격 최신 코드 받아오기 |
| `git push origin main` | 내 커밋을 GitHub에 업로드 |

---

## 🧠 6️⃣ 기본 작업 흐름

```bash
# 항상 작업 전 최신 코드 가져오기
git pull origin main

# 코드 수정 후
git add .
git commit -m "feat: 기능 추가"
git push origin main
```

> 💡 push할 때 처음 한 번만 토큰 입력 → 자동 저장됨

---

## ⚡ 7️⃣ 충돌(conflict) 발생 시
1. 에디터에서 `<<<<<<<`, `=======`, `>>>>>>>` 표시 확인  
2. 원하는 코드로 수정 후 저장  
3. 명령 실행:
```bash
git add .
git commit -m "fix: 충돌 해결"
git push origin main
```

---

## 🚀 8️⃣ 프로젝트 종료 후, 내 계정에 복사 (포트폴리오용)

1. 폴더로 이동
```bash
cd mini_project_3rd
```

2. 기존 원격 삭제
```bash
git remote remove origin
```

3. 내 GitHub에서 새 repo 생성 (README 없이)

4. 새 원격 등록 및 업로드
```bash
git remote add origin https://github.com/username/mini_project_3rd.git
git push -u origin main
```

> ✅ 이제 내 계정에 팀 프로젝트 복제 완료!

---

## ✅ 핵심 요약
> **clone → add → commit → pull → push → (완료 후 내 repo로 복사)**  
>  
> 🧩 push 전에 항상 pull  
> 🔒 `.env` 등 비밀 정보는 절대 올리지 말기
