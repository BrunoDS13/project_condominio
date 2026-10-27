/* Condomínio: tema, menu lateral, avisos, envio único e contagem animada. Sem dependências. */
(function () {
  'use strict';
  var reduz = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // --- tema: Sistema -> Claro -> Escuro (lembrado neste navegador) ---
  var ordem = [null, 'claro', 'escuro'], rotulos = { 'null': 'Auto', claro: 'Claro', escuro: 'Escuro' };
  function lerPref() { try { var p = localStorage.getItem('tema'); return p === 'claro' || p === 'escuro' ? p : null; } catch (e) { return null; } }
  function aplicar(pref) {
    var escuro = pref === 'escuro' || (!pref && window.matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.setAttribute('data-theme', escuro ? 'dark' : 'light');
    document.querySelectorAll('[data-tema-btn]').forEach(function (b) { b.textContent = 'Tema · ' + rotulos[pref]; });
  }
  var pref = lerPref();
  aplicar(pref);
  document.querySelectorAll('[data-tema-btn]').forEach(function (b) {
    b.addEventListener('click', function () {
      pref = ordem[(ordem.indexOf(pref) + 1) % ordem.length];
      try { pref ? localStorage.setItem('tema', pref) : localStorage.removeItem('tema'); } catch (e) {}
      aplicar(pref);
    });
  });
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () { if (!pref) aplicar(null); });

  // --- menu lateral no celular ---
  var btn = document.getElementById('menu-toggle'), bar = document.getElementById('sidebar'), scrim = document.getElementById('scrim');
  if (btn && bar) {
    var abrir = function (open) {
      bar.classList.toggle('open', open);
      if (scrim) scrim.classList.toggle('open', open);
      btn.setAttribute('aria-expanded', String(open));
      btn.textContent = open ? 'Fechar' : 'Menu';
    };
    btn.addEventListener('click', function () { abrir(!bar.classList.contains('open')); });
    if (scrim) scrim.addEventListener('click', function () { abrir(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') abrir(false); });
    bar.addEventListener('click', function (e) { if (e.target.closest('a')) abrir(false); });
  }

  // --- avisos: fechar e sumir sozinho os de sucesso ---
  function fechar(n) {
    if (reduz) { n.remove(); return; }
    n.style.transition = 'opacity 180ms, transform 180ms';
    n.style.opacity = '0'; n.style.transform = 'translateY(-6px)';
    setTimeout(function () { n.remove(); }, 190);
  }
  document.querySelectorAll('.notice').forEach(function (n) {
    var x = n.querySelector('.notice-x');
    if (x) x.addEventListener('click', function () { fechar(n); });
    if (n.classList.contains('success')) setTimeout(function () { if (n.isConnected) fechar(n); }, 6000);
  });

  // --- envio único: desabilita o botão principal ao enviar ---
  document.addEventListener('submit', function (e) {
    var b = e.target.querySelector('button.btn-primary[type=submit]');
    if (!b || e.defaultPrevented) return;
    setTimeout(function () { b.disabled = true; b.dataset.rotulo = b.textContent; b.textContent = 'Aguarde…'; }, 0);
  });
  window.addEventListener('pageshow', function () {
    document.querySelectorAll('button[data-rotulo]').forEach(function (b) { b.disabled = false; b.textContent = b.dataset.rotulo; });
  });

  // --- contagem animada dos valores-chave (o texto final já está no HTML) ---
  if (!reduz) {
    var fmt = {
      brl: new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }),
      int: new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 })
    };
    document.querySelectorAll('[data-count]').forEach(function (el) {
      var alvo = parseFloat(el.getAttribute('data-count')), tipo = el.getAttribute('data-fmt') || 'int', final = el.textContent;
      if (!isFinite(alvo) || alvo === 0) return;
      var ini = null, dur = 700;
      function passo(t) {
        if (ini === null) ini = t;
        var p = Math.min((t - ini) / dur, 1), e = 1 - Math.pow(1 - p, 3);
        el.textContent = fmt[tipo].format(alvo * e).replace(/ /g, ' ');
        if (p < 1) requestAnimationFrame(passo); else el.textContent = final;
      }
      requestAnimationFrame(passo);
    });
  }
})();
