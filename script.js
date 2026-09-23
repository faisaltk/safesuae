const menuToggle = document.querySelector('.menu-toggle');
const nav = document.querySelector('.nav');

menuToggle?.addEventListener('click', () => {
  nav.classList.toggle('open');
});

document.querySelectorAll('.product[data-link]').forEach(card => {
  card.addEventListener('click', (e) => {
    if (!e.target.closest('a')) window.location.href = card.dataset.link;
  });
  card.setAttribute('role', 'link');
  card.setAttribute('tabindex', '0');
  card.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') window.location.href = card.dataset.link;
  });
});

document.querySelectorAll('.nav a').forEach(link => {
  link.addEventListener('click', () => nav.classList.remove('open'));
});

const searchInput = document.getElementById('searchInput') || document.getElementById('catalogueSearch');
const products = [...document.querySelectorAll('.product, .product-card')];
const noResults = document.getElementById('noResults');

searchInput?.addEventListener('input', (e) => {
  const query = e.target.value.toLowerCase().trim();
  let visible = 0;

  products.forEach(product => {
    const text = ((product.dataset.search || '') + ' ' + product.innerText).toLowerCase();
    const match = text.includes(query);
    product.style.display = match ? '' : 'none';
    if (match) visible++;
  });

  if (noResults) noResults.style.display = visible ? 'none' : 'block';
});

const yearEl = document.getElementById('year');
if (yearEl) yearEl.textContent = new Date().getFullYear();


/* Swipeable product gallery */
document.querySelectorAll('[data-product-gallery]').forEach(gallery => {
  const images = [...gallery.querySelectorAll('[data-gallery-src]')].map(x => ({
    src: x.dataset.gallerySrc,
    alt: x.dataset.galleryAlt || ''
  }));
  const main = gallery.querySelector('.gallery-main img');
  const prev = gallery.querySelector('.gallery-arrow.prev');
  const next = gallery.querySelector('.gallery-arrow.next');
  const dots = gallery.querySelector('.gallery-dots');
  const thumbs = gallery.querySelector('.gallery-thumbs');
  if (!main || !images.length) return;

  let index = 0;
  const render = () => {
    const item = images[index];
    main.src = item.src;
    main.alt = item.alt;
    if (dots) [...dots.children].forEach((d,i)=>d.classList.toggle('active',i===index));
    if (thumbs) [...thumbs.children].forEach((d,i)=>d.classList.toggle('active',i===index));
    if (prev) prev.hidden = images.length < 2;
    if (next) next.hidden = images.length < 2;
  };
  images.forEach((item,i)=>{
    if(dots){
      const b=document.createElement('button');
      b.className='gallery-dot';
      b.type='button';
      b.setAttribute('aria-label','Show image '+(i+1));
      b.onclick=()=>{index=i;render()};
      dots.appendChild(b);
    }
    if(thumbs){
      const b=document.createElement('button');
      b.className='gallery-thumb';
      b.type='button';
      b.innerHTML='<img src="'+item.src+'" alt="">';
      b.onclick=()=>{index=i;render()};
      thumbs.appendChild(b);
    }
  });
  prev?.addEventListener('click',()=>{index=(index-1+images.length)%images.length;render()});
  next?.addEventListener('click',()=>{index=(index+1)%images.length;render()});

  let startX=0;
  gallery.querySelector('.gallery-main')?.addEventListener('touchstart',e=>{startX=e.changedTouches[0].clientX},{passive:true});
  gallery.querySelector('.gallery-main')?.addEventListener('touchend',e=>{
    const dx=e.changedTouches[0].clientX-startX;
    if(Math.abs(dx)>45 && images.length>1){
      index=(index+(dx<0?1:-1)+images.length)%images.length;
      render();
    }
  },{passive:true});
  render();
});

/* Automatically use imported product images */
(function loadImportedProductImages() {
  const imageFor = (slug) => '/products/images/' + slug + '.webp';

  document.querySelectorAll('.product-card').forEach(card => {
    const link = card.querySelector('a.view-btn[href*="product="]');
    const box = card.querySelector('.product-image');
    if (!link || !box) return;

    const match = link.href.match(/[?&]product=([^&#]+)/);
    if (!match) return;

    const slug = decodeURIComponent(match[1]);
    const img = new Image();
    img.alt = card.querySelector('h2')?.textContent?.trim() || 'Product image';
    img.loading = 'lazy';
    img.src = imageFor(slug);
    img.onload = () => {
      box.classList.remove('image-placeholder');
      box.innerHTML = '';
      box.appendChild(img);
    };
  });

  const detailName = document.getElementById('name');
  const detailBox = document.querySelector('.product-gallery .gallery-main');
  const key = new URLSearchParams(location.search).get('product');

  if (detailName && detailBox && key) {
    const img = new Image();
    img.alt = detailName.textContent.trim() + ' product image';
    img.loading = 'eager';
    img.src = imageFor(key);
    img.onload = () => {
      detailBox.classList.remove('image-placeholder');
      detailBox.innerHTML = '';
      detailBox.appendChild(img);
    };
  }
})();

