/* ===== VELTRIX CRM — Main JS ===== */

// قائمة المستخدم
function toggleMenu() {
    const menu = document.getElementById('userMenu');
    if (menu) menu.classList.toggle('show');
}

// إغلاق القائمة عند النقر خارجها
document.addEventListener('click', function(e) {
    const menu = document.getElementById('userMenu');
    if (menu && menu.classList.contains('show')) {
        const wrapper = menu.closest('.user-menu');
        if (wrapper && !wrapper.contains(e.target)) {
            menu.classList.remove('show');
        }
    }
});

// إخفاء رسائل الفلاش تلقائياً بعد 5 ثوانٍ
document.addEventListener('DOMContentLoaded', function() {
    const flashes = document.querySelectorAll('.flash');
    flashes.forEach(function(flash) {
        setTimeout(function() {
            flash.style.animation = 'slideIn .3s ease reverse';
            setTimeout(function() { flash.remove(); }, 300);
        }, 5000);
    });
    initLuxCursor();
    initHeroParallax();
});

// السايدبار في الموبايل
function toggleSidebar() {
    const sidebar = document.getElementById('adminSidebar');
    if (sidebar) {
        sidebar.style.display = sidebar.style.display === 'none' ? 'flex' : 'none';
    }
}

function initLuxCursor() {
    if (!window.matchMedia('(pointer: fine)').matches) return;

    const cursor = document.getElementById('luxCursor');
    if (!cursor) return;

    let mouseX = window.innerWidth / 2;
    let mouseY = window.innerHeight / 2;
    let cursorX = mouseX;
    let cursorY = mouseY;

    document.body.classList.add('cursor-ready');

    document.addEventListener('mousemove', function (e) {
        mouseX = e.clientX;
        mouseY = e.clientY;
        document.body.classList.add('cursor-ready');
    });

    function animateCursor() {
        cursorX += (mouseX - cursorX) * 0.14;
        cursorY += (mouseY - cursorY) * 0.14;
        cursor.style.transform = "translate(" + cursorX + "px, " + cursorY + "px)";
        requestAnimationFrame(animateCursor);
    }
    animateCursor();

    document.querySelectorAll('a, button, input, select, textarea, .cat-card, .product-card').forEach(function (el) {
        el.addEventListener('mouseenter', function () {
            document.body.classList.add('cursor-hover');
        });
        el.addEventListener('mouseleave', function () {
            document.body.classList.remove('cursor-hover');
        });
    });

    document.addEventListener('mousedown', function () {
        document.body.classList.add('cursor-down');
    });
    document.addEventListener('mouseup', function () {
        document.body.classList.remove('cursor-down');
    });
    document.addEventListener('mouseleave', function () {
        document.body.classList.remove('cursor-ready');
    });
}

function initHeroParallax() {
    const hero = document.querySelector('.hero');
    const visual = document.querySelector('.hero-visual');
    if (!hero || !visual || !window.matchMedia('(pointer: fine)').matches) return;

    hero.addEventListener('mousemove', function (e) {
        const rect = hero.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;
        visual.style.transform = "rotateY(" + (x * 10) + "deg) rotateX(" + (-y * 8) + "deg) translateZ(0)";
    });

    hero.addEventListener('mouseleave', function () {
        visual.style.transform = 'rotateY(0deg) rotateX(0deg)';
    });
}
