// ── Navbar scroll shadow + scroll-to-top visibility ──────────────
const navbar = document.getElementById('navbar');
const scrollTopBtn = document.getElementById('scrollTop');

window.addEventListener('scroll', () => {
    if (navbar) navbar.classList.toggle('scrolled', window.scrollY > 20);
    if (scrollTopBtn) scrollTopBtn.classList.toggle('visible', window.scrollY > 320);
});

if (scrollTopBtn) {
    scrollTopBtn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

// ── Flash messages: auto-dismiss + smooth close ───────────────────
document.addEventListener('DOMContentLoaded', () => {
    const dismissFlash = (el) => {
        el.style.transition = 'all 0.4s ease';
        el.style.opacity = '0';
        el.style.transform = 'translateX(110%)';
        setTimeout(() => el.remove(), 450);
    };

    document.querySelectorAll('.flash-close').forEach(btn => {
        btn.addEventListener('click', () => dismissFlash(btn.closest('.flash')));
    });

    const flashContainer = document.getElementById('flash-container');
    if (flashContainer) {
        setTimeout(() => {
            [...flashContainer.children].forEach((el, i) => {
                setTimeout(() => dismissFlash(el), i * 150);
            });
        }, 4000);
    }

    // ── Quantity buttons (cart & detail pages) ──────────────────────
    document.querySelectorAll('.qty-control').forEach(ctrl => {
        const input = ctrl.querySelector('.qty-val');
        const minusBtn = ctrl.querySelector('[data-action="minus"]');
        const plusBtn = ctrl.querySelector('[data-action="plus"]');

        if (minusBtn && plusBtn && input) {
            minusBtn.addEventListener('click', () => {
                const val = parseInt(input.value) || 1;
                if (val > 1) { input.value = val - 1; triggerChange(input); }
            });
            plusBtn.addEventListener('click', () => {
                const val = parseInt(input.value) || 1;
                input.value = val + 1;
                triggerChange(input);
            });
        }
    });

    // ── Address card selection ──────────────────────────────────────
    document.querySelectorAll('.address-card').forEach(card => {
        card.addEventListener('click', () => {
            document.querySelectorAll('.address-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            const radio = card.querySelector('input[type="radio"]');
            if (radio) radio.checked = true;
            const newAddrForm = document.getElementById('new-address-form');
            if (newAddrForm) {
                newAddrForm.style.display = radio.value === 'new' ? 'block' : 'none';
            }
        });
    });

    // ── Toggle new address form ─────────────────────────────────────
    const newAddrRadio = document.getElementById('radio-new');
    if (newAddrRadio) {
        newAddrRadio.addEventListener('change', () => {
            const form = document.getElementById('new-address-form');
            if (form) form.style.display = newAddrRadio.checked ? 'block' : 'none';
        });
    }

    // ── Product card scroll-in animation ───────────────────────────
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.08 });

    document.querySelectorAll('.product-card').forEach((el, i) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(28px)';
        el.style.transition = `opacity 0.5s ease ${i * 0.06}s, transform 0.5s ease ${i * 0.06}s, border-color 0.3s, box-shadow 0.3s`;
        observer.observe(el);
    });

    // ── Cart badge pulse after add-to-cart ─────────────────────────
    const badge = document.querySelector('.cart-badge');
    if (badge && document.referrer.includes('/cart/add/')) {
        badge.classList.add('pulse');
        setTimeout(() => badge.classList.remove('pulse'), 500);
    }

    // ── Ripple effect on primary buttons ──────────────────────────
    document.querySelectorAll('.btn-primary').forEach(btn => {
        btn.addEventListener('click', function (e) {
            const rect = this.getBoundingClientRect();
            const ripple = document.createElement('span');
            const size = Math.max(rect.width, rect.height);
            ripple.style.cssText = `
                position:absolute; border-radius:50%;
                width:${size}px; height:${size}px;
                left:${e.clientX - rect.left - size / 2}px;
                top:${e.clientY - rect.top - size / 2}px;
                background:rgba(255,255,255,0.25);
                transform:scale(0); animation:ripple 0.5s ease;
                pointer-events:none;
            `;
            this.appendChild(ripple);
            setTimeout(() => ripple.remove(), 500);
        });
    });
});

// Ripple keyframe (injected once)
if (!document.getElementById('ripple-style')) {
    const s = document.createElement('style');
    s.id = 'ripple-style';
    s.textContent = '@keyframes ripple { to { transform: scale(2.5); opacity: 0; } }';
    document.head.appendChild(s);
}

function triggerChange(el) {
    el.dispatchEvent(new Event('change', { bubbles: true }));
}

// ── Cart quantity auto-submit ─────────────────────────────────────
document.addEventListener('change', e => {
    if (e.target.classList.contains('qty-val') && e.target.closest('form[data-auto-submit]')) {
        e.target.closest('form').submit();
    }
});
