const menuToggle = document.querySelector('.menu-toggle');
const nav = document.querySelector('.nav');

menuToggle?.addEventListener('click', () => {
  nav.classList.toggle('open');
});

document.querySelectorAll('.nav a').forEach(link => {
  link.addEventListener('click', () => nav.classList.remove('open'));
});

const searchInput = document.getElementById('searchInput');
const products = [...document.querySelectorAll('.product')];
const noResults = document.getElementById('noResults');

searchInput?.addEventListener('input', (e) => {
  const query = e.target.value.toLowerCase().trim();
  let visible = 0;

  products.forEach(product => {
    const text = (product.dataset.search + ' ' + product.innerText).toLowerCase();
    const match = text.includes(query);
    product.style.display = match ? '' : 'none';
    if (match) visible++;
  });

  noResults.style.display = visible ? 'none' : 'block';
});

document.getElementById('year').textContent = new Date().getFullYear();
