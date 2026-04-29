# `docs/design/assets/` — 정적 자원

## LG Innotek 로고
- `lg-innotek-logo-en-white.png` — 다크 배경용 (영문 화이트)
- `lg-innotek-logo-en-gray.png` — 라이트 배경용 (영문 그레이)
- `lg-innotek-logo-ko-white.png` — 한국어 화이트

출처: lginnotek.com 공식 페이지 (Brand Identity).

## 배경 영상 (선택 — 자체 호스팅 시 자동 우선 적용)

랜딩 페이지의 배경 영상은 두 단계 fallback 구조입니다:

1. **`landing-bg.mp4`** (자체 호스팅) — 이 파일이 있으면 HTML5 `<video>` 태그로 재생됩니다.
   모바일 자동재생 제한이 거의 없어서 **재생버튼이 안 뜨고 일시정지도 안 발생**합니다.
2. **YouTube iframe** — 위 파일이 없으면 자동으로 YouTube 임베드로 fallback.

### 자체 호스팅 권장

YouTube iframe 은 모바일에서 자동재생이 자주 막혀서 (특히 Samsung Internet) 가운데에 재생버튼이 보이거나 탭 전환 시 일시정지됩니다. 경험을 100% 안정적으로 만들려면 영상을 직접 mp4 로 변환해 이 폴더에 올리세요.

### 파일 사양

| 파일명 | 권장 사양 |
|---|---|
| `landing-bg.mp4` | H.264 / AAC, 1920×1080, ~10-30 초 루프, **5MB 이하 권장** (raw.githack 캐싱 + 갤탭 모바일 데이터) |
| `landing-bg-poster.jpg` | 1920×1080 JPEG, 첫 프레임 또는 어두운 대표 컷 (옵션 — 영상 로딩 전 보임) |

### 변환 예시 (ffmpeg)

원본 YouTube 영상 (`https://youtu.be/lCOjL68zt0U`) 을 개인 다운로드 도구로 받아 mp4 로 갖고 있다면:

```bash
# 720p, 30초 루프, web-optimized, 압축
ffmpeg -i input.mp4 -t 30 -vf "scale=1920:-2" \
  -c:v libx264 -preset slow -crf 28 -an \
  -movflags +faststart \
  landing-bg.mp4

# 포스터 (1초 시점 프레임)
ffmpeg -i input.mp4 -ss 1 -vframes 1 -vf "scale=1920:-2" landing-bg-poster.jpg
```

### 라이선스

LG Innotek 공식 영상은 LG 그룹 자산입니다. 이 저장소가 GitHub public 인 동안엔 푸시 전 사내 권한 확인 필요. 사내망 배포 시에는 사내 CDN 또는 Streamlit `st.video()` 정적 자원으로 호스팅하는 게 안전합니다.

`landing-bg.mp4` 가 없어도 페이지는 동작합니다 (YouTube fallback).
