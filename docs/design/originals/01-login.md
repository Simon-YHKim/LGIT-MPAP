# Login (로그인)

> Variant tag: **S1** · Original file: `설빕생산성분석 플랫폼 로그인.html`

## Page title

`설빕생산성분석 플랫폼 로그인`

## Sidebar navigation (모든 페이지 공통)

```
login / Home / CMP Dashboard / UPH Dashboard / MTBA Dashboard / MTBA Detail View / MaxCapa Chat
```

## Visible labels (Korean, 원본 그대로)

- 로그인
- 회원가입
- 사내 계정 아이디만 입력하세요.
- @lginnotek.com 은 자동 적용됩니다.
- 아이디
- 비밀번호
- 회사 이메일 인증 후 사용 가능합니다.
- 회사 이메일
- 인증코드 발송


## Existing custom CSS (user-authored, 발견된 경우만)

```css
/* 전체 배경 */
.stApp {
    background-color: #fafafa;
}

/* 상단 헤더 */
.main-header {
    background: linear-gradient(90deg, #6f0f2a, #8c1d3c);
    padding: 26px 32px;
    border-radius: 20px;
    color: white;
    font-size: 30px;
    font-weight: 800;
    margin-bottom: 28px;
}

.main-header-sub {
    font-size: 14px;
    opacity: 0.85;
    margin-top: 6px;
}

/* 카드 영역 */
.card {
    background: white;
    padding: 28px 32px;
    border-radius: 18px;
    border: 1px solid #eee;
    box-shadow: 0 6px 22px rgba(0,0,0,0.04);
    margin-top: 12px;
}

/* 카드 제목 */
.card-title {
    font-size: 20px;
    font-weight: 700;
    color: #7b172e;
    margin-bottom: 14px;
}

/* 안내 문구 */
.card-desc {
    font-size: 14px;
    color: #555;
    margin-bottom: 16px;
}

/* 로그인 카드 컨테이너 */
div[data-testid="stVerticalBlock"]:has(.login-card-anchor) {
    background: white;
    padding: 32px 36px;
    border-radius: 18px;
    border: 1px solid #eee;
    box-shadow: 0 6px 22px rgba(0,0,0,0.06);
    max-width: 520px;
    margin: 0 auto;
}
```


## Notes for Claude Design

- 위 visible labels 의 한국어 문자열을 **그대로** 시안에 사용할 것 (의역·번역 금지)

- 사이드바 네비게이션 7개 항목과 순서·라벨 유지

- 기존 custom CSS 가 있어도 디자인 토큰은 `DESIGN.md` 기준을 따를 것 (참고만)
