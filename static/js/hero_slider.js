/* Carrusel de la portada (website/_hero_slider.html).
   Fundido entre slides, avance automático con pausa (botón, ratón encima,
   foco dentro o pestaña oculta), flechas, puntos, teclado y deslizar. */
(function () {
    'use strict';

    function init(root) {
        var slides = Array.prototype.slice.call(root.querySelectorAll('[data-hs-slide]'));
        if (slides.length < 2) return;

        var dots = Array.prototype.slice.call(root.querySelectorAll('[data-hs-dot]'));
        var pauseBtn = root.querySelector('[data-hs-pause]');
        var interval = parseInt(root.dataset.interval, 10) || 7000;
        var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        var current = 0;
        var timer = null;
        var userPaused = reduceMotion;   // sin movimiento automático si el usuario lo pide
        var hoverPaused = false;

        function show(index) {
            var next = (index + slides.length) % slides.length;
            if (next === current) return;
            setActive(slides[current], false);
            dots[current].removeAttribute('aria-current');
            current = next;
            setActive(slides[current], true);
            dots[current].setAttribute('aria-current', 'true');
        }

        function setActive(slide, active) {
            slide.classList.toggle('is-active', active);
            if (active) {
                slide.removeAttribute('aria-hidden');
                slide.inert = false;
            } else {
                slide.setAttribute('aria-hidden', 'true');
                slide.inert = true;
            }
        }

        function schedule() {
            clearInterval(timer);
            timer = null;
            if (userPaused || hoverPaused || document.hidden) return;
            timer = setInterval(function () { show(current + 1); }, interval);
        }

        function updatePauseButton() {
            if (!pauseBtn) return;
            pauseBtn.setAttribute('aria-label', userPaused ? pauseBtn.dataset.labelPlay : pauseBtn.dataset.labelPause);
            pauseBtn.innerHTML = '<i class="bi ' + (userPaused ? 'bi-play-fill' : 'bi-pause-fill') + '" aria-hidden="true"></i>';
        }

        function go(index) {
            show(index);
            schedule();   // reinicia la cuenta tras una acción del usuario
        }

        root.querySelector('[data-hs-prev]').addEventListener('click', function () { go(current - 1); });
        root.querySelector('[data-hs-next]').addEventListener('click', function () { go(current + 1); });
        dots.forEach(function (dot, i) {
            dot.addEventListener('click', function () { go(i); });
        });

        if (pauseBtn) {
            pauseBtn.addEventListener('click', function () {
                userPaused = !userPaused;
                updatePauseButton();
                schedule();
            });
        }

        root.addEventListener('mouseenter', function () { hoverPaused = true; schedule(); });
        root.addEventListener('mouseleave', function () { hoverPaused = false; schedule(); });
        root.addEventListener('focusin', function () { hoverPaused = true; schedule(); });
        root.addEventListener('focusout', function (e) {
            if (!root.contains(e.relatedTarget)) { hoverPaused = false; schedule(); }
        });
        document.addEventListener('visibilitychange', schedule);

        root.addEventListener('keydown', function (e) {
            if (e.key === 'ArrowLeft') { go(current - 1); }
            else if (e.key === 'ArrowRight') { go(current + 1); }
        });

        // Deslizar en pantallas táctiles
        var startX = null;
        var startY = null;
        root.addEventListener('touchstart', function (e) {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        }, { passive: true });
        root.addEventListener('touchend', function (e) {
            if (startX === null) return;
            var dx = e.changedTouches[0].clientX - startX;
            var dy = e.changedTouches[0].clientY - startY;
            if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy)) {
                swiped = true;
                go(dx < 0 ? current + 1 : current - 1);
            }
            startX = startY = null;
        });
        // Un deslizamiento no debe abrir el enlace del slide
        var swiped = false;
        root.addEventListener('click', function (e) {
            if (swiped) {
                e.preventDefault();
                swiped = false;
            }
        }, true);

        updatePauseButton();
        schedule();
    }

    document.querySelectorAll('[data-hs]').forEach(init);
})();
