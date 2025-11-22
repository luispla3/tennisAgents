// Navbar dropdown functionality
document.addEventListener('DOMContentLoaded', function() {
    // Dropdown toggle
    const tennisDropdown = document.getElementById('tennisDropdown');
    const tennisDropdownMenu = document.getElementById('tennisDropdownMenu');
    const tennisDropdownParent = tennisDropdown?.closest('.dropdown');

    if (tennisDropdown && tennisDropdownMenu) {
        tennisDropdown.addEventListener('click', function(e) {
            e.stopPropagation();
            tennisDropdownParent?.classList.toggle('active');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!tennisDropdownParent?.contains(e.target)) {
                tennisDropdownParent?.classList.remove('active');
            }
        });
    }

    // Mobile menu toggle
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const navbarLinks = document.querySelector('.navbar-links');

    if (mobileMenuToggle && navbarLinks) {
        mobileMenuToggle.addEventListener('click', function() {
            navbarLinks.classList.toggle('active');
            mobileMenuToggle.classList.toggle('active');
        });

        // Close mobile menu when clicking on a link
        const navLinks = navbarLinks.querySelectorAll('.nav-link, .dropdown-item');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                navbarLinks.classList.remove('active');
                mobileMenuToggle.classList.remove('active');
            });
        });
    }

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#' && href.startsWith('#')) {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });

    // Navbar scroll effect
    let lastScroll = 0;
    const navbar = document.querySelector('.navbar');

    window.addEventListener('scroll', function() {
        const currentScroll = window.pageYOffset;

        if (currentScroll > 100) {
            navbar?.classList.add('scrolled');
        } else {
            navbar?.classList.remove('scrolled');
        }

        lastScroll = currentScroll;
    });
});

