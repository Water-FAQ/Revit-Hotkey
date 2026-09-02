const menuButton = document.querySelector('.menu-toggle');
const navigation = document.querySelector('.nav');
const backToTop = document.querySelector('.back-to-top');

menuButton?.addEventListener('click', () => {
  const open = navigation.classList.toggle('open');
  menuButton.setAttribute('aria-expanded', String(open));
});

navigation?.addEventListener('click', (event) => {
  if (event.target.closest('a')) {
    navigation.classList.remove('open');
    menuButton?.setAttribute('aria-expanded', 'false');
  }
});

window.addEventListener('scroll', () => {
  backToTop?.classList.toggle('visible', window.scrollY > 520);
}, { passive: true });

backToTop?.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
