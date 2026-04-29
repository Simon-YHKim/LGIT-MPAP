# `docs/design/fonts/` — 자체 호스팅 폰트

웹페이지에서 LG Smart 폰트를 모든 사용자에게 동일하게 보여주려면, 폰트 바이너리(.woff2 / .ttf) 파일을 이 폴더에 직접 업로드해야 합니다.

## 현재 상태

`@font-face` 선언이 다음 순서로 폰트를 찾습니다 (각 페이지의 `<style>` 블록):

1. **이 폴더의 url() 파일** ← **여기에 업로드 필요**
2. 사용자 PC 에 설치된 LG Smart (`local()` fallback)
3. Pretendard CDN (외부 환경 graceful fallback)

지금은 1번이 비어있어서 **사내 PC** 에서는 2번(local LG Smart)이 적용되지만, **갤탭/외부망/모바일** 에서는 3번(Pretendard)이 적용됩니다.

이 폴더에 .woff2 파일을 올리는 순간 **모든 환경에서 LG Smart로 통일** 됩니다.

## 업로드 방법

다음 4개 파일 (또는 가능한 변형) 을 이 디렉토리에 추가:

```
fonts/
├── lg-smart-300.woff2   (Light)
├── lg-smart-400.woff2   (Regular)
├── lg-smart-600.woff2   (SemiBold)
└── lg-smart-700.woff2   (Bold)
```

권장 포맷: `.woff2` (압축률 좋음, 모든 모던 브라우저 지원).
대체: `.woff`, `.ttf` 도 동작 (각 페이지의 `@font-face` `src:` 에 추가 형식 필요시 알려주세요).

## 라이선스 메모

LG Smart 는 LG 그룹의 상표·저작권 자산입니다. 이 저장소가 GitHub public 으로 공개될 경우 폰트 파일을 그대로 커밋하기 전에 LG 코퍼레이트 디자인 가이드의 사용 권한 확인이 필요합니다. 업로드 후 외부 노출이 우려되면 다음 옵션 중 하나로 대응:

1. **저장소를 private 으로 변경** — 사내망 전용 사용을 명시
2. **빌드 시점 주입** — `.gitignore` 에 `fonts/*.woff2` 추가 + Streamlit 배포 환경에 별도 주입
3. **사내 폰트 서버에서 호스팅** — `@font-face url('https://internal-cdn.lginnotek.com/fonts/lg-smart.woff2')`

## 파일 업로드 후 적용 방법

폰트를 업로드하고 커밋·푸시하면, 이 저장소의 모든 18개 HTML 의 `@font-face` 가 자동으로 url() 을 우선 시도하므로 **추가 작업 불필요**합니다.

업로드 후 raw.githack URL 을 새로고침해 적용 확인 가능.
