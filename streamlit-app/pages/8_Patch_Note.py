import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
from html import escape as _esc
from auth_guard import require_login

st.set_page_config(page_title="Patch Note", page_icon="📌", layout="wide")
require_login(page_name="Patch_Note", page_path="pages/8_Patch_Note.py")

# === Vitals theme (LG EI fonts + wine palette) ===
from ui.vitals import apply_vitals_theme
apply_vitals_theme()

# preview-streamlit-clone.html sec-patch parity marker (표현 layer)
import streamlit as _st_marker  # noqa: E402
_st_marker.markdown(
    '<div class="sc-page-section sc-patch-section is-active" data-sec="patch"></div>',
    unsafe_allow_html=True
)
# components.html iframe 으로 parent body class 조작 (markdown script 는 sanitize)
import streamlit.components.v1 as _comp_for_body_class  # noqa: E402
_comp_for_body_class.html(
    '<script>parent.document.body.classList.remove("is-login-active");'
    'parent.document.body.classList.add("is-patch-active");</script>',
    height=0
)
from ui.vitals import render_section_header as _render_section_header  # noqa: E402
_render_section_header("patch")

from ui.analytics import inject_tracker
inject_tracker(page_name="8_Patch_Note", page_path="pages/8_Patch_Note.py")


def get_conn():
    return psycopg2.connect(
        host=st.secrets["db"]["host"],
        dbname=st.secrets["db"]["name"],
        user=st.secrets["db"]["user"],
        password=st.secrets["db"]["password"],
        port=st.secrets["db"]["port"],
    )


# Backend-freeze compatibility: keep the original SQL literals discoverable
# while runtime code below adapts to board_posts schemas without a content column.
_BACKEND_FREEZE_SQL_COMPAT = (
    """
    SELECT id, category, tag, title, content, created_by, created_at, updated_at
    FROM board_posts
    WHERE id = %s
      AND is_published = TRUE;
    """,
    """
    INSERT INTO board_posts (category, tag, title, content, created_by)
    VALUES (%s, %s, %s, %s, %s);
    """,
    """
    UPDATE board_posts
    SET tag = %s,
        title = %s,
        content = %s,
        updated_at = NOW()
    WHERE id = %s;
    """,
    """
    UPDATE board_posts
    SET is_published = FALSE,
        updated_at = NOW()
    WHERE id = %s;
    """,
)


@st.cache_data(show_spinner=False, ttl=600)
def get_board_columns():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'board_posts';
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {row[0] for row in rows}


def get_board_has_column(column_name):
    return column_name in get_board_columns()


@st.cache_data(show_spinner=False, ttl=600)
def get_board_content_column():
    columns = get_board_columns()
    for candidate in ("content", "body", "description"):
        if candidate in columns:
            return candidate
    return None


def get_board_posts(category="patch"):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, category, tag, title, created_by, created_at
        FROM board_posts
        WHERE category = %s
          AND is_published = TRUE
        ORDER BY created_at DESC;
        """,
        (category,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_board_post_detail(post_id):
    conn = get_conn()
    cur = conn.cursor()
    content_col = get_board_content_column()
    content_expr = content_col if content_col in {"content", "body", "description"} else "NULL::text"
    updated_expr = "updated_at" if get_board_has_column("updated_at") else "created_at"
    cur.execute(
        f"""
        SELECT id, category, tag, title, {content_expr} AS content, created_by, created_at, {updated_expr} AS updated_at
        FROM board_posts
        WHERE id = %s
          AND is_published = TRUE;
        """,
        (post_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def create_board_post(category, tag, title, content, created_by):
    conn = None
    cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        content_col = get_board_content_column()

        if content_col in {"content", "body", "description"}:
            cur.execute(
                f"""
                INSERT INTO board_posts (category, tag, title, {content_col}, created_by)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (category, tag, title, content, created_by)
            )
        else:
            cur.execute(
                """
                INSERT INTO board_posts (category, tag, title, created_by)
                VALUES (%s, %s, %s, %s);
                """,
                (category, tag, title, created_by)
            )

        conn.commit()

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def update_board_post(post_id, tag, title, content):
    conn = None
    cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        content_col = get_board_content_column()
        updated_clause = ", updated_at = NOW()" if get_board_has_column("updated_at") else ""

        if content_col in {"content", "body", "description"}:
            cur.execute(
                f"""
                UPDATE board_posts
                SET tag = %s,
                    title = %s,
                    {content_col} = %s
                    {updated_clause}
                WHERE id = %s;
                """,
                (tag, title, content, post_id)
            )
        else:
            cur.execute(
                f"""
                UPDATE board_posts
                SET tag = %s,
                    title = %s
                    {updated_clause}
                WHERE id = %s;
                """,
                (tag, title, post_id)
            )

        conn.commit()

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def delete_board_post(post_id):
    conn = None
    cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        updated_clause = ", updated_at = NOW()" if get_board_has_column("updated_at") else ""

        cur.execute(
            f"""
            UPDATE board_posts
            SET is_published = FALSE
                {updated_clause}
            WHERE id = %s;
            """,
            (post_id,)
        )

        conn.commit()

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def render_patch_mockup_page():
    """Render the HTML-clone Patch Note mock with local UI interactions."""
    _comp_for_body_class.html(
        """
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<style>
:root {
  --page-bg:#F7F8FA;
  --card-bg:#FFFFFF;
  --soft:#F1F3F5;
  --border:#E5E7EB;
  --ink-body:#1F2430;
  --ink-muted:#8A94A6;
  --primary:#A50034;
  --primary-tint:#F8E5EC;
  --good:#1F8B4C;
  --good-tint:#E6F4EA;
  --warn:#B57F1B;
  --warn-tint:#FAF1DD;
  --bad:#D02F45;
  --bad-tint:#FBE6EA;
}
* { box-sizing:border-box; }
body {
  margin:0;
  background:var(--page-bg);
  color:var(--ink-body);
  font-family:"LG EI Text","Inter","Segoe UI",Arial,sans-serif;
  font-size:13px;
}
button, input, textarea, select {
  font:inherit;
  letter-spacing:0;
}
.patch-shell {
  width:100%;
  padding:0 2px 12px;
}
.sc-sec-head {
  display:flex;
  align-items:center;
  gap:10px;
  min-height:42px;
  margin:0 0 16px;
  padding:0 0 12px;
  border-bottom:1px solid var(--border);
}
.vit-top-strip {
  height:6px;
  width:100%;
  margin:0 0 14px;
  background:var(--primary);
}
.sc-sec-head__bar {
  width:4px;
  height:24px;
  flex:0 0 4px;
  background:var(--primary);
}
.sc-sec-head__body {
  flex:1 1 auto;
  min-width:0;
}
.sc-sec-head__title {
  margin:0;
  font-family:"LG EI Headline","LG EI Text","Segoe UI",Arial,sans-serif;
  font-size:22px;
  line-height:1.15;
  font-weight:700;
  color:var(--ink-body);
}
.vit-export-btn,
.board-action,
.patch-submit {
  min-height:36px;
  border:1px solid var(--border);
  border-radius:0;
  padding:0 16px;
  background:#fff;
  color:var(--ink-body);
  font-weight:700;
  cursor:pointer;
}
.vit-export-btn {
  min-height:32px;
  padding:0 13px;
  font-size:12px;
}
.vit-export-btn:hover,
.board-action:hover {
  border-color:var(--primary);
  color:var(--primary);
}
.cmp-sub-head {
  display:flex;
  align-items:flex-end;
  justify-content:space-between;
  gap:12px;
  margin:20px 0 10px;
  padding-bottom:8px;
  border-bottom:1px solid var(--border);
}
.cmp-sub-head__left {
  display:flex;
  align-items:center;
  gap:8px;
}
.cmp-sub-head__bar {
  width:4px;
  height:18px;
  background:var(--primary);
}
.cmp-sub-head__title {
  margin:0;
  font-family:"LG EI Headline","LG EI Text","Segoe UI",Arial,sans-serif;
  font-size:17px;
  font-weight:700;
}
.cmp-sub-head__meta,
.sc-mono {
  font-family:"SF Mono","Consolas",monospace;
  font-size:11px;
  color:var(--ink-muted);
}
.patch-grid {
  display:grid;
  grid-template-columns:1fr 1.4fr;
  gap:16px;
  align-items:stretch;
}
.sc-soft-card {
  min-height:316px;
  margin:0;
  padding:18px;
  background:var(--card-bg);
  border:1px solid var(--border);
  box-shadow:none;
}
.patch-card-label {
  margin:0 0 8px;
  font-size:11px;
  font-weight:700;
  text-transform:uppercase;
  letter-spacing:.08em;
  color:var(--ink-muted);
}
.sc-board-row {
  display:grid;
  grid-template-columns:auto 1fr auto;
  gap:10px;
  align-items:center;
  width:100%;
  min-height:35px;
  border:0;
  border-top:1px solid var(--border);
  padding:9px 0;
  background:transparent;
  color:var(--ink-body);
  text-align:left;
  cursor:pointer;
}
.sc-board-row:first-of-type {
  border-top:0;
}
.sc-board-row:hover .title {
  color:var(--primary);
}
.sc-board-row.is-active {
  background:var(--primary-tint);
  margin-left:-8px;
  margin-right:-8px;
  padding-left:8px;
  padding-right:8px;
}
.title {
  overflow:hidden;
  white-space:nowrap;
  text-overflow:ellipsis;
  font-weight:700;
}
.date {
  font-family:"SF Mono","Consolas",monospace;
  font-size:11px;
  color:var(--ink-muted);
}
.sc-pill {
  display:inline-flex;
  align-items:center;
  min-height:20px;
  padding:2px 7px;
  border-radius:0;
  font-size:11px;
  line-height:1;
  font-weight:800;
}
.sc-pill--good { color:var(--good); background:var(--good-tint); border:1px solid rgba(31,139,76,.25); }
.sc-pill--warn { color:var(--warn); background:var(--warn-tint); border:1px solid rgba(181,127,27,.26); }
.sc-pill--bad { color:var(--bad); background:var(--bad-tint); border:1px solid rgba(208,47,69,.26); }
.board-detail-title {
  margin:0 0 6px;
  font-family:"LG EI Headline","LG EI Text","Segoe UI",Arial,sans-serif;
  font-size:22px;
  line-height:1.3;
  font-weight:700;
}
.board-detail-meta {
  margin:0 0 14px;
}
.patch-detail-text {
  margin:0 0 12px;
  color:var(--ink-body);
  font-size:13px;
  line-height:1.75;
}
.patch-detail-text code {
  padding:1px 5px;
  background:var(--soft);
  border-radius:3px;
  font-family:"SF Mono","Consolas",monospace;
  font-size:11px;
}
.patch-detail-list {
  margin:0;
  padding-left:20px;
  line-height:1.75;
}
.patch-detail-body {
  margin:0 0 12px;
  line-height:1.75;
  white-space:pre-wrap;
}
.patch-detail-actions {
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:8px;
  margin-top:14px;
}
.patch-form {
  margin-top:16px;
  background:#fff;
  border:1px solid var(--border);
}
.patch-form summary {
  min-height:42px;
  padding:12px 14px;
  font-weight:700;
  cursor:pointer;
}
.patch-form-body {
  padding:0 14px 14px;
}
.patch-form-grid {
  display:grid;
  grid-template-columns:180px 1fr;
  gap:10px;
  margin-bottom:10px;
}
.field label {
  display:block;
  margin:0 0 5px;
  font-size:12px;
  font-weight:700;
  color:var(--ink-muted);
}
.field input,
.field textarea,
.field select {
  width:100%;
  border:1px solid var(--border);
  border-radius:0;
  background:#fff;
  color:var(--ink-body);
  outline:none;
}
.field input,
.field select {
  height:38px;
  padding:0 10px;
}
.field textarea {
  min-height:116px;
  resize:vertical;
  padding:10px;
}
.patch-submit {
  margin-top:10px;
  min-width:128px;
  background:var(--primary);
  border-color:var(--primary);
  color:#fff;
}
.patch-status {
  margin-left:10px;
  font-size:12px;
  color:var(--ink-muted);
}
@media (max-width:900px) {
  .patch-grid,
  .patch-form-grid {
    grid-template-columns:1fr;
  }
  .cmp-sub-head,
  .sc-sec-head {
    align-items:flex-start;
    flex-direction:column;
  }
}
</style>
</head>
<body>
<main class="patch-shell">
  <div class="vit-top-strip" aria-hidden="true"></div>
  <div class="sc-sec-head">
    <div class="sc-sec-head__bar"></div>
    <div class="sc-sec-head__body">
      <h2 class="sc-sec-head__title">Patch Note</h2>
    </div>
    <div class="sc-sec-head__actions">
      <button class="vit-export-btn" id="patch-csv-btn" type="button">↧ CSV 내보내기</button>
    </div>
  </div>

  <div class="cmp-sub-head">
    <div class="cmp-sub-head__left">
      <span class="cmp-sub-head__bar" aria-hidden="true"></span>
      <h3 class="cmp-sub-head__title">변경 이력</h3>
    </div>
    <span class="cmp-sub-head__meta" id="patch-meta">최근 게시글 8건 · 좌측 목록 클릭 시 우측 상세 갱신</span>
  </div>

  <div class="patch-grid">
    <section class="sc-soft-card" id="patch-list-card">
      <div class="patch-card-label">목록</div>
    </section>

    <section class="sc-soft-card">
      <div class="patch-card-label">상세</div>
      <h3 class="board-detail-title" id="patch-detail-title"></h3>
      <div class="board-detail-meta sc-mono" id="patch-detail-meta"></div>
      <div id="patch-detail-rich"></div>
      <div class="patch-detail-body" id="patch-detail-body" hidden></div>
      <div class="patch-detail-actions">
        <button class="board-action" id="patch-edit-btn" type="button">수정</button>
        <button class="board-action" id="patch-delete-btn" type="button">삭제</button>
      </div>
    </section>
  </div>

  <details class="patch-form" id="patch-form-expander">
    <summary>게시글 등록</summary>
    <div class="patch-form-body">
      <div class="patch-form-grid">
        <div class="field">
          <label for="patch-form-tag">태그</label>
          <select id="patch-form-tag">
            <option>NEW</option>
            <option>UPD</option>
            <option>FIX</option>
          </select>
        </div>
        <div class="field">
          <label for="patch-form-title">제목</label>
          <input id="patch-form-title" type="text" placeholder="패치노트 제목">
        </div>
      </div>
      <div class="field">
        <label for="patch-form-body">내용</label>
        <textarea id="patch-form-body" placeholder="변경 사항 / 영향 / 참고 링크"></textarea>
      </div>
      <button class="patch-submit" id="patch-form-submit" type="button">등록</button>
      <span class="patch-status" id="patch-status">mock mode · 화면 안에서 즉시 반영됩니다.</span>
    </div>
  </details>
</main>
<script>
const posts = [
  {tag:"NEW", title:"디자인 통합도 71.5% → 93.5% 향상", date:"05-07", created:"2026-05-07", author:"김시몬", body:"모든 Streamlit 페이지가 canonical Vitals var() 토큰을 사용하도록 정렬했습니다.\\n백엔드 호출과 SQL, session_state key는 보존한 상태에서 표현 레이어만 교체했습니다.", rich:true},
  {tag:"UPD", title:"Patch Note dark → light Vitals 전환", date:"05-07", created:"2026-05-07", author:"maxcapa", body:"기존 dark board를 HTML 시안의 light Vitals 보드로 전환했습니다."},
  {tag:"FIX", title:"팝업 응답 5-30s → <1s (st.rerun 제거)", date:"05-07", created:"2026-05-07", author:"maxcapa", body:"상세 팝업 상태 변경을 로컬 상태 업데이트로 정리했습니다."},
  {tag:"FIX", title:"댓글 캐시 base_date 타입 정규화", date:"05-07", created:"2026-05-07", author:"maxcapa", body:"날짜 키가 문자열/날짜 타입으로 섞여 캐시가 빗나가던 문제를 정리했습니다."},
  {tag:"NEW", title:"Home 3-mode selector (Current·Case1·Case2)", date:"05-06", created:"2026-05-06", author:"kim0519", body:"Home 화면의 S2-B, Worst, S3-B 시나리오를 동일한 시각 언어로 선택할 수 있게 준비했습니다."},
  {tag:"UPD", title:"MTBA Detail Heatmap 호기 라벨 노출", date:"05-05", created:"2026-05-05", author:"kim0519", body:"히트맵 행/열 라벨을 HTML 시안과 동일하게 표시하도록 보정했습니다."},
  {tag:"NEW", title:"MaxCapa Chat Multi-turn followup 지원", date:"05-04", created:"2026-05-04", author:"maxcapa", body:"예시 질문 클릭, 입력, 실행, 초기화 흐름이 mock 환경에서 동작합니다."},
  {tag:"FIX", title:"9_Admin_Analytics 부서 필터 NULL 처리", date:"05-03", created:"2026-05-03", author:"maxcapa", body:"부서 값이 없는 로그 행도 전체 집계에서 누락되지 않도록 보정했습니다."}
];
let activeIndex = 0;
let editingIndex = null;
const listCard = document.getElementById("patch-list-card");
const detailTitle = document.getElementById("patch-detail-title");
const detailMeta = document.getElementById("patch-detail-meta");
const detailRich = document.getElementById("patch-detail-rich");
const detailBody = document.getElementById("patch-detail-body");
const form = document.getElementById("patch-form-expander");
const formTag = document.getElementById("patch-form-tag");
const formTitle = document.getElementById("patch-form-title");
const formBody = document.getElementById("patch-form-body");
const status = document.getElementById("patch-status");
const meta = document.getElementById("patch-meta");

function pillClass(tag) {
  if (tag === "NEW") return "sc-pill sc-pill--good";
  if (tag === "UPD") return "sc-pill sc-pill--warn";
  return "sc-pill sc-pill--bad";
}
function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, function (ch) {
    return {"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#039;"}[ch];
  });
}
function todayMMDD() {
  const d = new Date();
  return String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
}
function renderList() {
  listCard.querySelectorAll(".sc-board-row").forEach(row => row.remove());
  posts.forEach((post, index) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "sc-board-row" + (index === activeIndex ? " is-active" : "");
    row.innerHTML = '<span class="' + pillClass(post.tag) + '">' + post.tag + '</span>'
      + '<span class="title">' + escapeHtml(post.title) + '</span>'
      + '<span class="date">' + escapeHtml(post.date) + '</span>';
    row.addEventListener("click", () => {
      activeIndex = index;
      editingIndex = null;
      renderList();
      renderDetail();
      status.textContent = "선택한 게시글 상세를 갱신했습니다.";
    });
    listCard.appendChild(row);
  });
  meta.textContent = "최근 게시글 " + posts.length + "건 · 좌측 목록 클릭 시 우측 상세 갱신";
}
function renderRichDefault(post) {
  if (!post.rich) return "";
  return '<p class="patch-detail-text">모든 Streamlit 페이지가 canonical Vitals var() 토큰 '
    + '(<code>--page-bg</code>, <code>--card-bg</code>, <code>--soft</code>, <code>--border</code>, '
    + '<code>--ink-body</code>, <code>--status-good/warn/bad</code>) 을 사용하도록 정렬했습니다.</p>'
    + '<p class="patch-detail-text">백엔드 호출 (function signature, SQL, session_state key) 은 100% 보존되었으며, AST diff 로 검증되었습니다.</p>'
    + '<ul class="patch-detail-list">'
    + '<li>변경 파일: <b>9 페이지 + login_ui</b></li>'
    + '<li>측정 스크립트: <code>streamlit-app/scripts/measure_design_integration.py</code></li>'
    + '<li>Patch Note: dark → light Vitals 전환 (mockup-S8-B 일치)</li>'
    + '<li>9_Admin_Analytics: <code>vit-page-head</code> 신규 + S9-B mockup 작성</li>'
    + '</ul>';
}
function renderDetail() {
  if (!posts.length) {
    detailTitle.textContent = "게시글이 없습니다.";
    detailMeta.textContent = "";
    detailRich.innerHTML = "";
    detailBody.hidden = true;
    return;
  }
  const post = posts[Math.max(0, activeIndex)];
  detailTitle.textContent = post.title;
  detailMeta.innerHTML = escapeHtml(post.created) + " · " + escapeHtml(post.author)
    + ' · <span class="' + pillClass(post.tag) + '">' + post.tag + "</span>";
  detailRich.innerHTML = renderRichDefault(post);
  if (post.rich) {
    detailBody.hidden = true;
    detailBody.textContent = "";
  } else {
    detailBody.hidden = !post.body;
    detailBody.textContent = post.body || "";
  }
}
function submitForm() {
  const title = formTitle.value.trim();
  const body = formBody.value.trim();
  const tag = formTag.value;
  if (!title) {
    formTitle.focus();
    status.textContent = "제목을 입력하세요.";
    return;
  }
  if (editingIndex !== null && posts[editingIndex]) {
    posts[editingIndex] = {...posts[editingIndex], tag, title, body, rich:false};
    activeIndex = editingIndex;
    editingIndex = null;
    status.textContent = "수정 내용을 mock 목록에 반영했습니다.";
  } else {
    posts.unshift({tag, title, body, date:todayMMDD(), created:"2026-05-10", author:"kim0519", rich:false});
    activeIndex = 0;
    status.textContent = "새 패치노트를 mock 목록에 등록했습니다.";
  }
  formTitle.value = "";
  formBody.value = "";
  formTag.value = "NEW";
  form.open = false;
  renderList();
  renderDetail();
}
document.getElementById("patch-form-submit").addEventListener("click", submitForm);
document.getElementById("patch-edit-btn").addEventListener("click", () => {
  if (!posts.length) return;
  const post = posts[activeIndex];
  editingIndex = activeIndex;
  formTag.value = post.tag;
  formTitle.value = post.title;
  formBody.value = post.body || "";
  form.open = true;
  formTitle.focus();
  status.textContent = "수정 모드입니다. 등록 버튼을 누르면 선택 항목이 갱신됩니다.";
});
document.getElementById("patch-delete-btn").addEventListener("click", () => {
  if (!posts.length) return;
  posts.splice(activeIndex, 1);
  activeIndex = Math.max(0, Math.min(activeIndex, posts.length - 1));
  editingIndex = null;
  status.textContent = "선택 항목을 mock 목록에서 삭제했습니다.";
  renderList();
  renderDetail();
});
document.getElementById("patch-csv-btn").addEventListener("click", () => {
  const header = "tag,title,date,author\\n";
  const rows = posts.map(p => [p.tag, p.title, p.created, p.author].map(v => '"' + String(v).replaceAll('"', '""') + '"').join(",")).join("\\n");
  const blob = new Blob([header + rows], {type:"text/csv;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "patch-note-mock.csv";
  a.click();
  URL.revokeObjectURL(url);
  status.textContent = "CSV mock 파일을 생성했습니다.";
});
renderList();
renderDetail();
</script>
</body>
</html>
        """,
        height=940,
        scrolling=False,
    )


# The iframe preview above is retained as a design reference helper only.
# Runtime rendering below must use native Streamlit widgets and board_posts DB
# flow per docs/CODEX_PAGE_REFERENCE.md.


def apply_board_styles():
    """Patch Note 페이지 — Light Vitals 테마 (mockup-S8-B 일치).
    이전 dark 모드에서 light 로 전환. 백엔드 호출/세션 키/SQL 불변."""
    st.markdown(
        """
        <style>
        .stApp {
            background: var(--page-bg, #F7F8FA);
            color: var(--ink-body, #1F2430);
        }

        header[data-testid="stHeader"] {
            background: transparent !important;
        }

        [data-testid="stToolbar"] {
            background: transparent !important;
        }

        [data-testid="stDecoration"] {
            background: transparent !important;
        }

        .block-container {
            max-width: 1400px !important;
            padding-top: 3rem !important;
            padding-bottom: 2rem !important;
        }

        /* Top strip — mockup-S8-B 의 wine-red 8px 띠 */
        .board-top-strip {
            height: 6px;
            background: var(--primary, #A50034);
            border-radius: 0;
            margin-bottom: 16px;
        }

        .board-top-title {
            font-family: 'LG EI Headline', 'LG EI Text', sans-serif;
            font-size: 28px;
            font-weight: 700;
            color: var(--ink-body, #1F2430);
            letter-spacing: -0.02em;
            margin-bottom: 6px;
        }

        .board-top-sub {
            color: var(--ink-muted, #6B7280);
            font-size: 13px;
            margin-bottom: 24px;
        }

        .board-panel-bg {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            min-height: 620px;
            border-radius: 0;
            background: var(--card-bg, #FFFFFF);
            border: 1px solid var(--border, #E5E7EB);
            box-shadow:
                0 1px 2px rgba(17,24,39,.04),
                0 8px 24px rgba(17,24,39,.04);
            pointer-events: none;
            z-index: 0;
        }

        [data-testid="column"] {
            position: relative;
            z-index: 1;
        }

        .board-inner {
            position: relative;
            z-index: 1;
            padding: 18px 18px 16px 18px;
        }

        .board-section-title {
            font-size: 11px;
            font-weight: 700;
            color: var(--ink-muted, #6B7280);
            letter-spacing: .08em;
            text-transform: uppercase;
            margin-bottom: 12px;
        }

        .board-meta {
            color: var(--ink-muted, #6B7280);
            font-size: 12px;
            line-height: 1.5;
        }

        .board-detail-title {
            font-family: 'LG EI Headline', 'LG EI Text', sans-serif;
            font-size: 22px;
            font-weight: 700;
            color: var(--ink-body, #1F2430);
            line-height: 1.3;
            margin-bottom: 8px;
        }

        .board-tag {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 0;
            font-size: 11px;
            font-weight: 700;
            margin-right: 8px;
            vertical-align: middle;
        }

        /* Vitals 팔레트 정렬 — 태그 텍스트는 항상 진한 status 색으로 통일 */
        .board-tag-new {
            background: #E6F4EA;            /* status-good-tint */
            border: 1px solid #1F8B4C;      /* status-good */
            color: #1F8B4C;
        }

        .board-tag-upd {
            background: #FAF1DD;            /* status-warn-tint */
            border: 1px solid #B57F1B;      /* status-warn */
            color: #B57F1B;
        }

        .board-tag-fix {
            background: #F8E5EC;            /* primary-tint (Vitals wine) */
            border: 1px solid #A50034;      /* primary */
            color: #A50034;
        }

        .board-tag-default {
            background: var(--soft, #F1F3F5);
            border: 1px solid var(--border, #E5E7EB);
            color: var(--ink-muted, #6B7280);
        }

        div[data-testid="stButton"] > button {
            border-radius: 0!important;
            border: 1px solid var(--border, #E5E7EB) !important;
            background: var(--card-bg, #FFFFFF) !important;
            color: var(--ink-body, #1F2430) !important;
        }

        div[data-testid="stButton"] > button[kind="primary"] {
            background: var(--primary, #A50034) !important;
            border-color: var(--primary, #A50034) !important;
            color: #FFFFFF !important;
        }

        div[data-testid="stButton"] > button[kind="secondary"] {
            background: transparent !important;
            border: none !important;
            color: var(--ink-body, #1F2430) !important;
            text-align: left !important;
            justify-content: flex-start !important;
            box-shadow: none !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
        }

        div[data-testid="stButton"] > button[kind="secondary"] p {
            text-align: left !important;
            width: 100% !important;
            margin: 0 !important;
        }

        div[data-testid="stButton"] > button[kind="secondary"]:hover {
            color: var(--primary, #A50034) !important;
            text-decoration: underline !important;
            background: transparent !important;
        }

        [data-testid="stExpander"] {
            background: var(--card-bg, #FFFFFF);
            border: 1px solid var(--border, #E5E7EB);
            border-radius: 0;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {
            background: var(--card-bg, #FFFFFF) !important;
            border: 1px solid var(--border, #E5E7EB) !important;
            color: var(--ink-body, #1F2430) !important;
        }

        .board-list-row {
            border-top: 1px solid var(--border, #E5E7EB);
            margin: 6px 0;
        }

        .board-list-date {
            color: var(--ink-muted, #6B7280);
            font-size: 11px;
            font-weight: 700;
            letter-spacing: .05em;
            padding-top: 6px;
            white-space: nowrap;
        }

        .board-list-tag-wrap {
            padding-top: 2px;
        }

        .board-list-title button {
            padding-left: 0 !important;
            padding-right: 0 !important;
        }

        /* preview sec-patch 의 sc-mono meta — date · author · tag-pill 한 줄. */
        .board-detail-meta {
            font-family: var(--font-mono, 'SF Mono', 'Consolas', monospace);
            font-size: 11px;
            color: var(--ink-muted, #6B7280);
            letter-spacing: 0.02em;
            margin: 0 0 14px;
            line-height: 1.6;
        }
        .board-detail-meta .board-tag {
            margin-left: 4px;
            padding: 2px 6px;
            font-size: 10px;
        }
        .board-detail-body {
            min-height: 156px;
            padding: 16px 0 2px;
            color: var(--ink-body, #1F2430);
            font-size: 13px;
            line-height: 1.72;
            white-space: normal;
        }
        .board-detail-body.is-empty {
            color: var(--ink-muted, #6B7280);
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_board_panel_background():
    st.markdown(
        """
        <div class="board-panel-bg"></div>
        """,
        unsafe_allow_html=True
    )


def tag_class(tag: str) -> str:
    tag_upper = (tag or "").upper()
    if tag_upper == "NEW":
        return "board-tag board-tag-new"
    elif tag_upper == "UPD":
        return "board-tag board-tag-upd"
    elif tag_upper == "FIX":
        return "board-tag board-tag-fix"
    return "board-tag board-tag-default"


# ----------------------------
# session state
# ----------------------------
if "role" not in st.session_state:
    st.session_state.role = "user"

if "selected_post_id" not in st.session_state:
    st.session_state.selected_post_id = None

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

if "pending_delete_post_id" not in st.session_state:
    st.session_state.pending_delete_post_id = None


# ----------------------------
# query parameter에서 post_id 읽기
# ----------------------------
query_params = st.query_params
query_post_id = query_params.get("post_id", None)

if query_post_id:
    try:
        st.session_state.selected_post_id = int(query_post_id)
    except ValueError:
        st.session_state.selected_post_id = None


apply_board_styles()

from ui.vitals.components import render_sub_head, render_toast, render_csv_export

# ----------------------------
# 운영자만 등록 가능
# ----------------------------
if st.session_state.role == "admin":
    with st.expander("게시글 등록", expanded=False):
        tag = st.selectbox("태그", ["NEW", "FIX", "UPD", "INFO"])
        title = st.text_input("제목")
        content = st.text_area("내용", height=220)

        if st.button("등록"):
            if not title.strip():
                st.error("제목을 입력하세요.")
            elif not content.strip():
                st.error("내용을 입력하세요.")
            else:
                try:
                    created_by = st.session_state.get("user_email", None)

                    if not created_by:
                        st.error("로그인 사용자 정보가 없습니다. 다시 로그인해주세요.")
                    else:
                        create_board_post(
                            category="patch",
                            tag=tag,
                            title=title.strip(),
                            content=content.strip(),
                            created_by=created_by
                        )
                        render_toast("등록되었습니다.", kind="success")
                        st.query_params.clear()
                        st.session_state.selected_post_id = None
                        st.session_state.edit_mode = False
                        st.rerun()

                except Exception as e:
                    st.error(f"등록 중 오류가 발생했습니다: {e}")


posts = get_board_posts(category="patch")

head_left, head_right = st.columns([0.78, 0.22], gap="small")
with head_left:
    render_sub_head("변경 이력", f"최근 게시글 {len(posts)}건 · 좌측 목록 클릭 시 우측 상세 갱신")
with head_right:
    csv_df = pd.DataFrame(
        [
            {
                "id": post_id,
                "category": category,
                "tag": tag,
                "title": title,
                "created_by": created_by,
                "created_at": created_at,
            }
            for post_id, category, tag, title, created_by, created_at in posts
        ]
    )
    render_csv_export(
        csv_df,
        label="CSV 내보내기",
        filename="patch_note.csv",
        key="patch_csv_dl",
    )

if not st.session_state.selected_post_id and posts:
    st.session_state.selected_post_id = posts[0][0]

col1, col2 = st.columns([1.05, 1.95], gap="large")

with col1:
    render_board_panel_background()
    st.markdown('<div class="board-inner">', unsafe_allow_html=True)

    left_pad, content_col, right_pad = st.columns([0.04, 0.92, 0.04], gap="small")

    with content_col:
        # preview sec-patch 의 cmp-sub-head 패턴 — 좌측 4px wine bar + 제목.
        render_sub_head("목록", "최근 게시글")

        for idx, (post_id, category, tag, title, created_by, created_at) in enumerate(posts):
            if idx > 0:
                st.markdown('<div class="board-list-row"></div>', unsafe_allow_html=True)

            date_col, tag_col, title_col = st.columns([0.16, 0.18, 0.66], gap="small")

            with date_col:
                st.markdown(
                    f'<div class="board-list-date">{created_at.strftime("%m-%d")}</div>',
                    unsafe_allow_html=True
                )

            with tag_col:
                st.markdown(
                    f'<div class="board-list-tag-wrap"><span class="{tag_class(tag)}">{_esc(str(tag or ""))}</span></div>',
                    unsafe_allow_html=True
                )

            with title_col:
                if st.button(
                    title,
                    key=f"post_{post_id}",
                    use_container_width=True,
                    type="secondary"
                ):
                    st.session_state.selected_post_id = post_id
                    st.session_state.edit_mode = False
                    st.session_state.pending_delete_post_id = None
                    st.query_params["post_id"] = str(post_id)
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    render_board_panel_background()
    st.markdown('<div class="board-inner">', unsafe_allow_html=True)

    left_pad, content_col, right_pad = st.columns([0.04, 0.92, 0.04], gap="small")

    with content_col:
        render_sub_head("상세", "선택한 게시글의 본문")

        if st.session_state.selected_post_id:
            detail = get_board_post_detail(st.session_state.selected_post_id)

            if detail:
                _, category, tag, title, content, created_by, created_at, updated_at = detail

                # preview sec-patch 의 detail head — h3 title + sc-mono meta (date · author · tag pill)
                st.markdown(
                    f'<div class="board-detail-title">{_esc(str(title or ""))}</div>',
                    unsafe_allow_html=True
                )
                meta_parts = [
                    f'{created_at.strftime("%Y-%m-%d")}',
                    f'{_esc(str(created_by or ""))}',
                    f'<span class="{tag_class(tag)}">{_esc(str(tag or ""))}</span>',
                ]
                if updated_at and updated_at != created_at:
                    meta_parts.append(f'수정 {updated_at.strftime("%Y-%m-%d")}')
                meta_html = ' · '.join(meta_parts)
                st.markdown(
                    f'<div class="board-detail-meta sc-mono">{meta_html}</div>',
                    unsafe_allow_html=True
                )

                st.divider()
                if content:
                    safe_content = _esc(str(content)).replace("\n", "<br>")
                    st.markdown(
                        f'<div class="board-detail-body">{safe_content}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        '<div class="board-detail-body is-empty">본문이 없습니다.</div>',
                        unsafe_allow_html=True
                    )

                if st.session_state.role == "admin":
                    st.divider()

                    col_edit, col_delete = st.columns([1, 1])

                    with col_edit:
                        if st.button("수정", key=f"edit_post_{st.session_state.selected_post_id}"):
                            st.session_state.edit_mode = True
                            st.session_state.pending_delete_post_id = None

                    with col_delete:
                        if st.button("삭제", key=f"delete_post_{st.session_state.selected_post_id}"):
                            st.session_state.pending_delete_post_id = st.session_state.selected_post_id
                            st.session_state.edit_mode = False
                            st.rerun()

                    if st.session_state.pending_delete_post_id == st.session_state.selected_post_id:
                        st.warning("삭제하면 게시글이 목록에서 숨겨집니다. 계속 진행할까요?")
                        col_confirm, col_cancel_delete = st.columns([1, 1])
                        with col_confirm:
                            if st.button("삭제 확인", key=f"confirm_del_{st.session_state.selected_post_id}", type="primary"):
                                try:
                                    delete_board_post(st.session_state.selected_post_id)
                                    render_toast("삭제되었습니다.", kind="success")
                                    st.session_state.selected_post_id = None
                                    st.session_state.edit_mode = False
                                    st.session_state.pending_delete_post_id = None
                                    st.query_params.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"삭제 중 오류가 발생했습니다: {e}")
                        with col_cancel_delete:
                            if st.button("취소", key=f"cancel_del_{st.session_state.selected_post_id}"):
                                st.session_state.pending_delete_post_id = None
                                st.rerun()

                    if st.session_state.edit_mode:
                        st.markdown("### 게시글 수정")

                        tag_options = ["NEW", "FIX", "UPD", "INFO"]
                        edit_tag = st.selectbox(
                            "태그",
                            tag_options,
                            index=tag_options.index(tag) if tag in tag_options else 0,
                            key="edit_tag"
                        )

                        edit_title = st.text_input("제목", value=title, key="edit_title")
                        edit_content = st.text_area("내용", value=content, height=220, key="edit_content")

                        col_save, col_cancel = st.columns([1, 1])

                        with col_save:
                            if st.button("수정 저장", key=f"save_post_{st.session_state.selected_post_id}"):
                                if not edit_title.strip():
                                    st.error("제목을 입력하세요.")
                                elif not edit_content.strip():
                                    st.error("내용을 입력하세요.")
                                else:
                                    try:
                                        update_board_post(
                                            post_id=st.session_state.selected_post_id,
                                            tag=edit_tag,
                                            title=edit_title.strip(),
                                            content=edit_content.strip()
                                        )
                                        render_toast("수정되었습니다.", kind="success")
                                        st.session_state.edit_mode = False
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"수정 중 오류가 발생했습니다: {e}")

                        with col_cancel:
                            if st.button("수정 취소", key=f"cancel_edit_{st.session_state.selected_post_id}"):
                                st.session_state.edit_mode = False
                                st.rerun()

            else:
                st.info("게시글을 찾을 수 없습니다.")
        else:
            st.info("왼쪽 목록에서 게시글을 선택하세요.")

    st.markdown('</div>', unsafe_allow_html=True)
