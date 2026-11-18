/* Simposio landing: countdown, day tabs, FAQ, and the motion layer (GSAP + Lenis).
   Everything works without the libraries; they only add movement. */
(function () {
    'use strict';

    var root = document.documentElement;
    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var gsap = window.gsap;
    var animated = !!(gsap && window.ScrollTrigger) && !reduceMotion;

    function all(selector, scope) {
        return Array.prototype.slice.call((scope || document).querySelectorAll(selector));
    }

    /* ---------- Countdown to the first session */
    (function () {
        var box = document.getElementById('spCountdown');
        if (!box) return;
        var start = new Date(box.dataset.start).getTime();
        var units = {};
        all('[data-unit]', box).forEach(function (el) { units[el.dataset.unit] = el; });
        var pad = function (n) { return (n < 10 ? '0' : '') + n; };
        var timer;
        function tick() {
            var left = Math.floor((start - Date.now()) / 1000);
            if (isNaN(left) || left <= 0) { box.hidden = true; clearInterval(timer); return; }
            box.hidden = false;
            units.d.textContent = Math.floor(left / 86400);
            units.h.textContent = pad(Math.floor(left % 86400 / 3600));
            units.m.textContent = pad(Math.floor(left % 3600 / 60));
            units.s.textContent = pad(left % 60);
        }
        tick();
        timer = setInterval(tick, 1000);
    })();

    /* ---------- Day tabs */
    (function () {
        var tabs = all('.sp-daybtn');
        if (!tabs.length) return;
        function select(tab, focus, animate) {
            var panel;
            tabs.forEach(function (other) {
                var on = other === tab;
                other.setAttribute('aria-selected', on ? 'true' : 'false');
                other.tabIndex = on ? 0 : -1;
                var target = document.getElementById(other.getAttribute('aria-controls'));
                target.hidden = !on;
                if (on) panel = target;
            });
            if (focus) tab.focus();
            if (animate && animated && panel) {
                gsap.from(all('.sp-slot', panel), {
                    y: 18, autoAlpha: 0, duration: .5, ease: 'power3.out', stagger: .035,
                    clearProps: 'all',
                });
                window.ScrollTrigger.refresh();
            }
        }
        tabs.forEach(function (tab, index) {
            tab.addEventListener('click', function () {
                if (tab.getAttribute('aria-selected') !== 'true') select(tab, false, true);
            });
            tab.addEventListener('keydown', function (event) {
                if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft' &&
                    event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
                event.preventDefault();
                var step = (event.key === 'ArrowRight' || event.key === 'ArrowDown') ? 1 : -1;
                select(tabs[(index + step + tabs.length) % tabs.length], true, true);
            });
        });
        select(tabs[0]);
    })();

    /* ---------- Highlight the section in view on the event bar */
    (function () {
        var links = all('.sp-nav a[href^="#"]');
        if (!('IntersectionObserver' in window) || !links.length) return;
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;
                links.forEach(function (link) {
                    if (link.getAttribute('href') === '#' + entry.target.id) link.setAttribute('aria-current', 'true');
                    else link.removeAttribute('aria-current');
                });
            });
        }, { rootMargin: '-45% 0px -50% 0px' });
        links.forEach(function (link) {
            var section = document.querySelector(link.getAttribute('href'));
            if (section) observer.observe(section);
        });
    })();

    /* ---------- Phone: show the registration dock once the hero button is gone */
    (function () {
        var dock = document.getElementById('spDock');
        var actions = document.getElementById('spHeroActions');
        if (!dock || !actions || !('IntersectionObserver' in window)) return;
        new IntersectionObserver(function (entries) {
            dock.classList.toggle('is-on', !entries[0].isIntersecting && entries[0].boundingClientRect.top < 0);
        }).observe(actions);
    })();

    /* ---------- FAQ: open and close with a height animation */
    if (animated) {
        all('.sp-faq details').forEach(function (item) {
            var summary = item.querySelector('summary');
            var answer = item.querySelector('.sp-faq-a');
            if (!summary || !answer) return;
            summary.addEventListener('click', function (event) {
                event.preventDefault();
                gsap.killTweensOf(answer);
                if (item.open && !item.classList.contains('is-closing')) {
                    item.classList.add('is-closing');
                    gsap.to(answer, {
                        height: 0, duration: .35, ease: 'power2.inOut',
                        onComplete: function () {
                            item.open = false;
                            item.classList.remove('is-closing');
                            gsap.set(answer, { clearProps: 'height' });
                        },
                    });
                } else {
                    item.classList.remove('is-closing');
                    item.open = true;
                    gsap.fromTo(answer, { height: answer.offsetHeight < 4 ? 0 : answer.offsetHeight },
                        { height: 'auto', duration: .45, ease: 'power3.out', clearProps: 'height' });
                }
            });
        });
    }

    if (!animated) { root.classList.remove('sp-anim'); return; }

    /* =====================================================================
       Motion layer
       ===================================================================== */
    var ScrollTrigger = window.ScrollTrigger;
    var SplitText = window.SplitText;
    var MotionPathPlugin = window.MotionPathPlugin;
    gsap.registerPlugin.apply(gsap, [ScrollTrigger, SplitText, MotionPathPlugin].filter(Boolean));

    /* Smooth scroll, driven by GSAP's ticker so both share one frame loop */
    if (window.Lenis) {
        var lenis = new window.Lenis({ anchors: true });
        lenis.on('scroll', ScrollTrigger.update);
        gsap.ticker.add(function (time) { lenis.raf(time * 1000); });
        gsap.ticker.lagSmoothing(0);
    }

    /* Hero entrance: one orchestrated sequence */
    root.classList.remove('sp-anim');
    var intro = gsap.timeline({ defaults: { ease: 'expo.out', duration: 1.2 } });
    intro
        .from('.sp-kv', { autoAlpha: 0, duration: .01 }, 0)
        .from('.sp-kv-photo', { scale: .55, autoAlpha: 0, duration: 1.5 }, 0)
        .from('.sp-orbits', { scale: .7, rotation: -50, autoAlpha: 0, svgOrigin: '300 300', duration: 1.8 }, .1)
        .from('.sp-hero-line > span', { yPercent: 112, stagger: .13 }, .15)
        .from('.sp-hero-copy [data-intro]', { y: 26, autoAlpha: 0, stagger: .1, duration: 1 }, .45)
        .fromTo('.sp-wave path', { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 1.1, ease: 'power2.out' }, 1.15)
        .from('.sp-seal', { scale: 0, rotation: -120, ease: 'back.out(1.5)', duration: 1 }, .9)
        .from('.sp-pass', { y: 70, autoAlpha: 0 }, .7);

    /* The seal's lettering turns; the electrons travel their orbits */
    gsap.to('.sp-seal-ring', { rotation: 360, svgOrigin: '80 80', duration: 26, ease: 'none', repeat: -1 });
    gsap.to('.sp-ring', { rotation: 360, svgOrigin: '300 300', duration: 120, ease: 'none', repeat: -1 });
    if (MotionPathPlugin) {
        /* Each electron is drawn twice: one copy behind the photo and one in front,
           shown only on the near half of the orbit, so it passes behind the city. */
        var travel = function (name, duration, start) {
            var front = document.getElementById('spElectron' + name);
            var back = document.getElementById('spElectron' + name + '2');
            if (!front || !back) return;
            gsap.set([front, back], { attr: { cx: 0, cy: 0 } });
            gsap.to([front, back], {
                motionPath: { path: '#spOrbit' + name, start: start, end: start + 1 },
                duration: duration, ease: 'none', repeat: -1,
                onUpdate: function () {
                    front.style.opacity = ((start + this.progress()) % 1) < .5 ? 1 : 0;
                },
            });
        };
        travel('A', 13, 0);
        travel('B', 19, .55);
    }

    /* Scroll-linked depth */
    var heroScroll = { trigger: '.sp-hero', start: 'top top', end: 'bottom top', scrub: true };
    gsap.to('.sp-kv-photo img', { yPercent: 6, ease: 'none', scrollTrigger: heroScroll });
    gsap.to('.sp-kv-svg', { rotation: 16, ease: 'none', scrollTrigger: heroScroll });
    all('[data-parallax] img').forEach(function (image) {
        gsap.fromTo(image, { yPercent: -5 }, {
            yPercent: 5, ease: 'none',
            scrollTrigger: { trigger: image.parentNode, start: 'top bottom', end: 'bottom top', scrub: true },
        });
    });
    gsap.to('.sp-close-orbits g', {
        rotation: 50, svgOrigin: '300 300', ease: 'none',
        scrollTrigger: { trigger: '.sp-close', start: 'top bottom', end: 'bottom top', scrub: true },
    });
    gsap.to('.sp-bar-progress', {
        scaleX: 1, ease: 'none',
        scrollTrigger: { start: 0, end: 'max', scrub: .3 },
    });

    /* Text: headings rise line by line */
    if (SplitText) {
        all('[data-reveal]').forEach(function (heading) {
            SplitText.create(heading, {
                type: 'lines', mask: 'lines', autoSplit: true,
                onSplit: function (self) {
                    return gsap.from(self.lines, {
                        yPercent: 105, duration: .9, ease: 'expo.out', stagger: .09,
                        scrollTrigger: { trigger: heading, start: 'top 88%', once: true },
                    });
                },
            });
        });
    }

    /* The figures panel: its orbits turn slowly with the scroll */
    gsap.to('.sp-figs-orbits', {
        rotation: 30, svgOrigin: '300 300', ease: 'none',
        scrollTrigger: { trigger: '.sp-figs', start: 'top bottom', end: 'bottom top', scrub: true },
    });

    /* Figures count up once */
    all('[data-count]').forEach(function (el) {
        var end = parseInt(el.dataset.count, 10);
        if (isNaN(end)) return;
        var state = { value: 0 };
        el.textContent = '0';
        gsap.to(state, {
            value: end, duration: 1.6, ease: 'power2.out',
            scrollTrigger: { trigger: el, start: 'top 90%', once: true },
            onUpdate: function () { el.textContent = Math.round(state.value); },
        });
    });

    /* Lists arrive together, once */
    all('[data-stagger]').forEach(function (group) {
        gsap.from(group.children, {
            y: 32, autoAlpha: 0, duration: .8, ease: 'power3.out', stagger: .07,
            scrollTrigger: { trigger: group, start: 'top 84%', once: true },
        });
    });

    window.addEventListener('load', function () { ScrollTrigger.refresh(); });
})();
