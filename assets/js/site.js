// 모바일 메뉴 열기/닫기
(function () {
  var btn = document.querySelector('.menu-btn');
  if (!btn) return;
  btn.addEventListener('click', function () {
    var open = document.body.classList.toggle('menu-open');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
})();
