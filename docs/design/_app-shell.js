/* ===================================================================
 * VITALS app shell — shared behavior for all logged-in pages
 * Usage:
 *   1. <link rel="stylesheet" href="./_app-shell.css">
 *   2. <script src="./_app-shell.js" defer></script>
 *   3. Define window.__I18N_PAGE__ = { ko: {...}, en: {...}, ... } per page
 *   4. Optional: window.__I18N_BASE__ shared across pages (this file owns it)
 * =================================================================== */

(function(){

  /* ---- shared base i18n strings (chrome only) -------------------- */
  window.__I18N_BASE__ = {
    ko:{
      "nav.heading":"메뉴","sidebar.intranet":"사내망",
      "nav.home":"Home","nav.cmp":"CMP 현황판","nav.uph":"UPH 현황판",
      "nav.mtba":"MTBA","nav.mtba_board":"MTBA 현황판","nav.mtba_by_process":"공정별 MTBA","nav.chat":"MaxCapa Chat",
      "topbar.logout":"로그아웃","topbar.menu":"메뉴 토글",
      "brand.team":"생산혁신센터 · Max Capa 팀",
      "chat.title":"MaxCapa Chat","chat.live":"LIVE",
      "chat.hint_title":"데이터소스 자동 분기",
      "chat.hint_body":"기본 조회는 MES UPH",
      "chat.hint_body2":"\"ITAS\" 키워드 포함 시 ITAS UPH",
      "chat.examples_title":"예시 질문",
      "chat.ex1":"R53A 모델 어제 UPH 평균은?",
      "chat.ex2":"ITAS 기준 R50 지난주 UPH 추이",
      "chat.ex3":"A2 라인에서 가장 느린 호기 5개",
      "chat.ex4":"CMP 미달 공정만 3월 4주차",
      "chat.empty_title":"대화 비어 있음",
      "chat.empty_body":"위 예시를 클릭하거나<br>아래에 자연어로 질문하세요.",
      "chat.src_label":"데이터소스",
      "chat.placeholder":"공정 / 모델 / 기간을 포함해 자연어로 질문하세요.",
      "chat.send":"질문 분석 및 실행",
      "chat.collapse":"패널 접기","chat.expand":"패널 펼치기",
      "foot.creator":"제작 · 생산혁신센터 Max Capa 팀",
      "foot.changelog":"변경 로그 전체 보기 →"
    },
    en:{
      "nav.heading":"MENU","sidebar.intranet":"Intranet",
      "nav.home":"Home","nav.cmp":"CMP Board","nav.uph":"UPH Board",
      "nav.mtba":"MTBA","nav.mtba_board":"MTBA Board","nav.mtba_by_process":"MTBA by Process","nav.chat":"MaxCapa Chat",
      "topbar.logout":"Logout","topbar.menu":"Toggle menu",
      "brand.team":"Production Innovation Center · Max Capa Team",
      "chat.title":"MaxCapa Chat","chat.live":"LIVE",
      "chat.hint_title":"Auto-routed data source",
      "chat.hint_body":"Default query is MES UPH",
      "chat.hint_body2":"With \"ITAS\" keyword it routes to ITAS UPH",
      "chat.examples_title":"Examples",
      "chat.ex1":"What was R53A average UPH yesterday?",
      "chat.ex2":"R50 UPH trend last week, ITAS basis",
      "chat.ex3":"Top 5 slowest machines on A2 line",
      "chat.ex4":"CMP shortfall processes only, Mar week 4",
      "chat.empty_title":"Empty thread",
      "chat.empty_body":"Tap an example above<br>or ask in natural language below.",
      "chat.src_label":"Source",
      "chat.placeholder":"Ask in natural language. Include process / model / period.",
      "chat.send":"Analyze & Run",
      "chat.collapse":"Collapse","chat.expand":"Expand",
      "foot.creator":"Built by · Production Innovation Center · Max Capa Team",
      "foot.changelog":"View full changelog →"
    },
    vi:{"nav.home":"Home","nav.cmp":"Bảng CMP","nav.uph":"Bảng UPH","nav.mtba":"MTBA","nav.mtba_board":"Bảng MTBA","nav.mtba_by_process":"MTBA theo công đoạn","nav.chat":"MaxCapa Chat","topbar.logout":"Đăng xuất","brand.team":"Trung tâm Đổi mới · Đội Max Capa","chat.send":"Phân tích & Chạy","chat.collapse":"Thu gọn","chat.expand":"Mở rộng","foot.creator":"Đội Max Capa · Trung tâm Đổi mới Sản xuất"},
    pl:{"nav.home":"Home","nav.cmp":"Tablica CMP","nav.uph":"Tablica UPH","nav.mtba":"MTBA","nav.mtba_board":"Tablica MTBA","nav.mtba_by_process":"MTBA wg procesu","nav.chat":"MaxCapa Chat","topbar.logout":"Wyloguj","brand.team":"Centrum Innowacji · Zespół Max Capa","chat.send":"Analizuj","chat.collapse":"Zwiń","chat.expand":"Rozwiń","foot.creator":"Zespół Max Capa · Centrum Innowacji Produkcji"},
    id:{"nav.home":"Home","nav.cmp":"Papan CMP","nav.uph":"Papan UPH","nav.mtba":"MTBA","nav.mtba_board":"Papan MTBA","nav.mtba_by_process":"MTBA per Proses","nav.chat":"MaxCapa Chat","topbar.logout":"Keluar","brand.team":"Pusat Inovasi · Tim Max Capa","chat.send":"Analisis","chat.collapse":"Ciutkan","chat.expand":"Bentangkan","foot.creator":"Tim Max Capa · Pusat Inovasi Produksi"},
    es:{"nav.home":"Home","nav.cmp":"Panel CMP","nav.uph":"Panel UPH","nav.mtba":"MTBA","nav.mtba_board":"Panel MTBA","nav.mtba_by_process":"MTBA por proceso","nav.chat":"MaxCapa Chat","topbar.logout":"Cerrar sesión","brand.team":"Centro de Innovación · Equipo Max Capa","chat.send":"Analizar","chat.collapse":"Contraer","chat.expand":"Expandir","foot.creator":"Equipo Max Capa · Centro de Innovación de Producción"},
    zh:{"nav.home":"Home","nav.cmp":"CMP 看板","nav.uph":"UPH 看板","nav.mtba":"MTBA","nav.mtba_board":"MTBA 看板","nav.mtba_by_process":"工序 MTBA","nav.chat":"MaxCapa Chat","topbar.logout":"登出","brand.team":"生产革新中心 · Max Capa 团队","chat.send":"分析并执行","chat.collapse":"收起","chat.expand":"展开","foot.creator":"Max Capa 团队 · 生产革新中心"}
  };

  /* ---- i18n apply ------------------------------------------------- */
  function lookup(code, key){
    var sources = [window.__I18N_PAGE__||{}, window.__I18N_BASE__];
    for (var s=0;s<sources.length;s++){
      var pack = sources[s][code]; if (pack && pack[key]!=null) return pack[key];
      var fb = sources[s].ko;     if (fb && fb[key]!=null) return fb[key];
    }
    return null;
  }
  function applyLang(code){
    document.documentElement.setAttribute('lang', code);
    document.querySelectorAll('[data-i18n]').forEach(function(el){
      var v = lookup(code, el.getAttribute('data-i18n'));
      if (v == null) return;
      if (v.indexOf('<br>') !== -1) el.innerHTML = v; else el.textContent = v;
    });
    document.querySelectorAll('[data-i18n-ph]').forEach(function(el){
      var v = lookup(code, el.getAttribute('data-i18n-ph'));
      if (v != null) el.setAttribute('placeholder', v);
    });
    document.querySelectorAll('[data-i18n-aria]').forEach(function(el){
      var v = lookup(code, el.getAttribute('data-i18n-aria'));
      if (v != null) el.setAttribute('aria-label', v);
    });
    var btn = document.getElementById('lang-current');
    if (btn) btn.textContent = code.toUpperCase();
    document.querySelectorAll('.lang__item').forEach(function(it){
      it.classList.toggle('lang__item--active', it.getAttribute('data-lang') === code);
    });
    localStorage.setItem('mpap.lang', code);
  }

  /* ---- ready ------------------------------------------------------ */
  function init(){
    /* lang */
    var langWrap = document.getElementById('lang');
    var langBtn  = document.getElementById('lang-btn');
    if (langWrap && langBtn) {
      langBtn.addEventListener('click', function(e){
        e.stopPropagation();
        var open = langWrap.classList.toggle('is-open');
        langBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
      document.addEventListener('click', function(e){
        if (!langWrap.contains(e.target)) {
          langWrap.classList.remove('is-open');
          langBtn.setAttribute('aria-expanded', 'false');
        }
      });
      document.querySelectorAll('.lang__item').forEach(function(it){
        it.addEventListener('click', function(){
          applyLang(it.getAttribute('data-lang'));
          langWrap.classList.remove('is-open');
        });
      });
    }

    /* sidebar collapse */
    var sb = document.getElementById('sidebar');
    var sbToggle = document.getElementById('sidebar-toggle');
    var sbMenu   = document.getElementById('topbar-menu');
    if (sb) {
      var sbCollapsed = localStorage.getItem('app.sidebar.collapsed') === '1';
      function applySb(){
        sb.classList.toggle('is-collapsed', sbCollapsed);
        localStorage.setItem('app.sidebar.collapsed', sbCollapsed ? '1' : '0');
      }
      applySb();
      function toggleSb(){ sbCollapsed = !sbCollapsed; applySb(); }
      if (sbToggle) sbToggle.addEventListener('click', toggleSb);
      if (sbMenu)   sbMenu.addEventListener('click', toggleSb);
    }

    /* chat panel */
    var panel  = document.getElementById('chat-panel');
    var handle = document.getElementById('chat-handle');
    var ctgl   = document.getElementById('chat-toggle');
    if (panel) {
      var WMIN=280, WMAX=720, WDEF=360;
      var savedW = parseInt(localStorage.getItem('app.chat.width') || String(WDEF), 10);
      if (isNaN(savedW)) savedW = WDEF;
      var defaultCollapsed = panel.getAttribute('data-default') === 'collapsed';
      var saved = localStorage.getItem('app.chat.collapsed');
      var collapsed = (saved === null) ? defaultCollapsed : (saved === '1');
      function clampW(w){ return Math.min(WMAX, Math.max(WMIN, w)); }
      function applyPanel(){
        panel.classList.toggle('is-collapsed', collapsed);
        if (!collapsed) panel.style.width = clampW(savedW) + 'px';
        else            panel.style.width = '';
      }
      applyPanel();
      if (ctgl) ctgl.addEventListener('click', function(){
        collapsed = !collapsed;
        localStorage.setItem('app.chat.collapsed', collapsed ? '1' : '0');
        applyPanel();
      });
      var dragging=false, startX=0, startW=0;
      if (handle) {
        handle.addEventListener('mousedown', function(e){
          if (collapsed) return;
          dragging=true; startX=e.clientX; startW=panel.offsetWidth;
          handle.classList.add('is-active');
          document.body.style.cursor='col-resize';
          document.body.style.userSelect='none';
          e.preventDefault();
        });
        document.addEventListener('mousemove', function(e){
          if (!dragging) return;
          var dx = startX - e.clientX;
          savedW = clampW(startW + dx);
          panel.style.width = savedW + 'px';
        });
        document.addEventListener('mouseup', function(){
          if (!dragging) return;
          dragging=false;
          handle.classList.remove('is-active');
          document.body.style.cursor='';
          document.body.style.userSelect='';
          localStorage.setItem('app.chat.width', String(savedW));
        });
      }
    }

    /* sidebar nav tree toggle */
    document.querySelectorAll('.nav__group').forEach(function(grp){
      var head = grp.querySelector('.nav__group__head');
      var key = grp.id || 'nav-group';
      var hasActive = !!grp.querySelector('.nav__item--active');
      var saved = localStorage.getItem('app.'+key+'.open');
      var open = (saved === null) ? (hasActive || true) : (saved === '1');
      function applyGrp(){
        grp.classList.toggle('is-open', open);
        if (hasActive) grp.classList.add('nav__group--has-active');
      }
      applyGrp();
      if (head) head.addEventListener('click', function(){
        open = !open;
        localStorage.setItem('app.'+key+'.open', open ? '1' : '0');
        applyGrp();
      });
    });

    /* modal — open via [data-modal-target=#id], close via .modal__close or overlay click */
    document.querySelectorAll('[data-modal-target]').forEach(function(trigger){
      trigger.addEventListener('click', function(e){
        var sel = trigger.getAttribute('data-modal-target');
        var modal = document.querySelector(sel);
        if (modal) { modal.classList.add('is-open'); document.body.style.overflow='hidden'; e.preventDefault(); }
      });
    });
    document.querySelectorAll('.modal-overlay').forEach(function(overlay){
      overlay.addEventListener('click', function(e){
        if (e.target === overlay || e.target.closest('.modal__close')) {
          overlay.classList.remove('is-open');
          document.body.style.overflow='';
        }
      });
    });
    document.addEventListener('keydown', function(e){
      if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.is-open').forEach(function(o){
          o.classList.remove('is-open');
        });
        document.body.style.overflow='';
      }
    });

    /* example chips → composer */
    var input = document.getElementById('chat-input');
    document.querySelectorAll('.chat-example').forEach(function(btn){
      btn.addEventListener('click', function(){
        var span = btn.querySelector('[data-i18n]');
        if (input && span) { input.value = span.textContent; input.focus(); }
      });
    });

    /* logout */
    document.querySelectorAll('[data-action="logout"]').forEach(function(btn){
      btn.addEventListener('click', function(e){
        e.preventDefault();
        try { localStorage.removeItem('mpap.session'); } catch(_){}
        window.location.href = './landing.html';
      });
    });

    /* apply current lang */
    var current = localStorage.getItem('mpap.lang') || 'ko';
    applyLang(current);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.__appShell = { applyLang: applyLang };

})();
