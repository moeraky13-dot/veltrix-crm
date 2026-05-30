/* مصباح تفاعلي — نفس آلية smartaim.org/auth.html (سحب الحبل + تشغيل/إطفاء) */
(function () {
    document.addEventListener('DOMContentLoaded', function () {
        const lampSvg = document.getElementById('lampSvg');
        const cord = document.getElementById('cord');
        const hit = document.getElementById('hit');
        const eyeL = document.getElementById('eyeL');
        const eyeR = document.getElementById('eyeR');
        const faceMouth = document.getElementById('faceMouth');
        const lampLight = document.getElementById('lampLight');
        const shadeBody = document.getElementById('shadeBody');
        const shadeOpening = document.getElementById('shadeOpening');
        const baseSide = document.getElementById('baseSide');
        const baseTop = document.getElementById('baseTop');
        const post = document.getElementById('post');
        const authBox = document.getElementById('authBox');

        if (!hit || !lampSvg || !authBox) return;

        const AX = 124, AY = 222;
        const RX = 124, RY = 348;

        let isOn = false;
        let dragging = false;
        let startScreen = { x: 0, y: 0 };
        let startSVG = { x: 0, y: 0 };
        const sp = { x: RX, y: RY, vx: 0, vy: 0 };
        let raf = null;

        function toSVG(sx, sy) {
            const pt = lampSvg.createSVGPoint();
            pt.x = sx;
            pt.y = sy;
            return pt.matrixTransform(lampSvg.getScreenCTM().inverse());
        }

        function drawCord(ex, ey) {
            const dx = ex - AX;
            const cpx = AX + dx * 0.25;
            const cpy = AY + (ey - AY) * 0.55 + Math.abs(dx) * 0.35;
            if (cord) cord.setAttribute('d', 'M' + AX + ',' + AY + ' Q' + cpx + ',' + cpy + ' ' + ex + ',' + ey);
        }

        function runSpring() {
            if (raf) cancelAnimationFrame(raf);
            const K = 200, D = 8;
            let last = performance.now();

            function step(now) {
                const dt = Math.min((now - last) / 1000, 0.032);
                last = now;
                sp.vx += (-K * (sp.x - RX) - D * sp.vx) * dt;
                sp.vy += (-K * (sp.y - RY) - D * sp.vy) * dt;
                sp.x += sp.vx * dt;
                sp.y += sp.vy * dt;
                drawCord(sp.x, sp.y);
                if (Math.abs(sp.x - RX) > 0.3 || Math.abs(sp.y - RY) > 0.3 || Math.abs(sp.vx) > 0.5 || Math.abs(sp.vy) > 0.5) {
                    raf = requestAnimationFrame(step);
                } else {
                    sp.x = RX;
                    sp.y = RY;
                    sp.vx = 0;
                    sp.vy = 0;
                    drawCord(RX, RY);
                }
            }
            raf = requestAnimationFrame(step);
        }

        function toggleLamp() {
            isOn = !isOn;
            const hue = Math.floor(Math.random() * 360);
            const glow = 'hsl(' + hue + ',40%,45%)';
            document.documentElement.style.setProperty('--auth-glow-color', glow);

            if (isOn) {
                const shadeCol = 'hsl(' + hue + ',30%,45%)';
                shadeBody.setAttribute('fill', shadeCol);
                shadeOpening.setAttribute('fill', 'hsl(' + hue + ',60%,70%)');
                baseSide.setAttribute('fill', 'hsl(' + hue + ',10%,55%)');
                baseTop.setAttribute('fill', 'hsl(' + hue + ',10%,65%)');
                post.setAttribute('fill', 'hsl(' + hue + ',10%,70%)');
                cord.setAttribute('stroke', '#ccc');
                lampLight.setAttribute('opacity', '1');
                faceMouth.setAttribute('opacity', '1');
                eyeL.setAttribute('d', 'M89 145c0-5.523 5.82-10 13-10s13 4.477 13 10');
                eyeR.setAttribute('d', 'M215 145c0-5.523 5.82-10 13-10s13 4.477 13 10');
                authBox.classList.add('active');
                lampSvg.classList.add('is-on');
            } else {
                shadeBody.setAttribute('fill', '#3a3a3a');
                shadeOpening.setAttribute('fill', '#222');
                baseSide.setAttribute('fill', '#505a60');
                baseTop.setAttribute('fill', '#606a70');
                post.setAttribute('fill', '#505a60');
                cord.setAttribute('stroke', '#888');
                lampLight.setAttribute('opacity', '0');
                faceMouth.setAttribute('opacity', '0');
                eyeL.setAttribute('d', 'M115 135c0-5.523-5.82-10-13-10s-13 4.477-13 10');
                eyeR.setAttribute('d', 'M241 135c0-5.523-5.82-10-13-10s-13 4.477-13 10');
                authBox.classList.remove('active');
                lampSvg.classList.remove('is-on');
            }

            sp.vy = 300;
            runSpring();
        }

        hit.addEventListener('mousedown', function (e) {
            dragging = true;
            if (raf) cancelAnimationFrame(raf);
            startScreen = { x: e.clientX, y: e.clientY };
            startSVG = toSVG(e.clientX, e.clientY);
            e.preventDefault();
        });

        hit.addEventListener('touchstart', function (e) {
            dragging = true;
            if (raf) cancelAnimationFrame(raf);
            const t = e.touches[0];
            startScreen = { x: t.clientX, y: t.clientY };
            startSVG = toSVG(t.clientX, t.clientY);
            e.preventDefault();
        }, { passive: false });

        document.addEventListener('mousemove', function (e) {
            if (!dragging) return;
            const sv = toSVG(e.clientX, e.clientY);
            sp.x = RX + (sv.x - startSVG.x);
            sp.y = RY + Math.max(0, sv.y - startSVG.y);
            drawCord(sp.x, sp.y);
        });

        document.addEventListener('touchmove', function (e) {
            if (!dragging) return;
            const t = e.touches[0];
            const sv = toSVG(t.clientX, t.clientY);
            sp.x = RX + (sv.x - startSVG.x);
            sp.y = RY + Math.max(0, sv.y - startSVG.y);
            drawCord(sp.x, sp.y);
            e.preventDefault();
        }, { passive: false });

        document.addEventListener('mouseup', function (e) {
            if (!dragging) return;
            dragging = false;
            const dist = Math.hypot(e.clientX - startScreen.x, e.clientY - startScreen.y);
            if (dist > 40) toggleLamp();
            else runSpring();
        });

        document.addEventListener('touchend', function (e) {
            if (!dragging) return;
            dragging = false;
            const t = e.changedTouches[0];
            const dist = Math.hypot(t.clientX - startScreen.x, t.clientY - startScreen.y);
            if (dist > 40) toggleLamp();
            else runSpring();
        });

        drawCord(RX, RY);
    });
})();
