// 태블릿 메뉴 열기/닫기
(function () {
  var btn = document.querySelector('.menu-btn');
  if (!btn) return;
  btn.addEventListener('click', function () {
    var open = document.body.classList.toggle('menu-open');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
})();

// 폰 메뉴 (원본 Wix 모바일과 같은 햄버거 / 전체 화면 메뉴)
(function () {
  var burger = document.querySelector('.m-burger');
  var menu = document.getElementById('m-menu');
  if (!burger || !menu) return;
  var close = menu.querySelector('.m-close');

  function setOpen(open) {
    menu.hidden = !open;
    document.body.classList.toggle('m-open', open);
    burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) close.focus(); else burger.focus();
  }
  burger.addEventListener('click', function () { setOpen(true); });
  close.addEventListener('click', function () { setOpen(false); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !menu.hidden) setOpen(false);
  });
  // 메뉴 바깥(어두운 부분)을 탭하면 닫기
  document.addEventListener('click', function (e) {
    if (menu.hidden || menu.contains(e.target) || burger.contains(e.target)) return;
    setOpen(false);
  });

  // 2013-2020 접기/펼치기
  menu.querySelectorAll('.m-chev').forEach(function (chev) {
    chev.addEventListener('click', function () {
      var li = chev.parentElement;
      var open = li.classList.toggle('open');
      chev.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  });

  // 맨 위로
  var top = document.querySelector('.m-top');
  if (top) {
    top.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'smooth' }); });
    var onScroll = function () { document.body.classList.toggle('scrolled', window.scrollY > 200); };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }
})();
