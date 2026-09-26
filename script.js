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

/* Product thumbnail/image loader */
(function loadImportedProductImages() {
  // Build the image URL from the live site's origin so this works on safesuae.com
  // and does not depend on the folder the current HTML page lives in.
  const siteRoot = window.location.origin;
  const imageUrl = (slug) => siteRoot + '/products/images/' + encodeURIComponent(slug) + '.webp';

  const attachImage = (box, slug, alt, eager = false) => {
    if (!box || !slug) return;

    const img = new Image();
    img.alt = alt || 'Product image';
    img.decoding = 'async';
    img.loading = eager ? 'eager' : 'lazy';
    img.className = 'catalogue-product-img';

    const show = () => {
      box.classList.remove('image-placeholder');
      box.innerHTML = '';
      box.appendChild(img);
    };

    img.addEventListener('load', show, { once: true });
    img.addEventListener('error', () => {
      // Keep the designed placeholder if an image is genuinely unavailable.
      box.classList.add('image-placeholder');
    }, { once: true });

    img.src = imageUrl(slug);
  };

  document.querySelectorAll('.product-card').forEach(card => {
    const link = card.querySelector('a.view-btn[href*="product="]');
    const box = card.querySelector('.product-image');
    if (!link || !box) return;

    const match = link.getAttribute('href')?.match(/[?&]product=([^&#]+)/);
    if (!match) return;

    const slug = decodeURIComponent(match[1]);
    const title = card.querySelector('h2, h3')?.textContent?.trim() || 'Product image';
    attachImage(box, slug, title, false);
  });

  const detailName = document.getElementById('name');
  const detailBox = document.querySelector('.product-gallery .gallery-main');
  const key = new URLSearchParams(window.location.search).get('product');

  if (detailName && detailBox && key) {
    attachImage(detailBox, key, detailName.textContent.trim() + ' product image', true);
  }
})();


/* Random product slideshow on the homepage gallery */
(function initProductSlideshow() {
  const slideshow = document.getElementById('productSlideshow');
  if (!slideshow) return;

  const image = document.getElementById('slideshowImage');
  const name = document.getElementById('slideshowName');
  const category = document.getElementById('slideshowCategory');
  const progress = document.getElementById('slideshowProgress');
  const prev = document.getElementById('slideshowPrev');
  const next = document.getElementById('slideshowNext');

  const imageUrl = (slug) => '/products/images/' + encodeURIComponent(slug) + '.webp';
  const imageFallbackUrl = (slug) => {
    if (slug === 'eagle-es-100') return '/products/images/ES-100.webp';
    return '';
  };
  const productUrl = (slug) => '/products/product-detail.html?product=' + encodeURIComponent(slug);
  const fallbackProducts = [
    {slug:'eagle-es-100',name:'Eagle ES-100',category:'LARGE COMMERCIAL'}
  ];

  let products = [];
  let order = [];
  let position = 0;
  let timer = null;
  let progressTimer = null;
  let busy = false;

  const shuffle = (items) => {
    const result = [...items];
    for (let i = result.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [result[i], result[j]] = [result[j], result[i]];
    }
    return result;
  };

  const resetProgress = () => {
  };

  image.setAttribute('role','link');
  image.setAttribute('tabindex','0');
  image.setAttribute('title','View product');
  image.style.cursor='pointer';

  const openCurrentProduct = () => {
    const product = order[position];
    if (product?.slug) window.location.href = productUrl(product.slug);
  };

  image.addEventListener('click', openCurrentProduct);
  image.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openCurrentProduct();
    }
  });

  const showProduct = (product, animate = true) => {
    if (!product) return;

    const apply = () => {
      image.onerror = () => {
        const fallback = imageFallbackUrl(product.slug);
        if (fallback && image.src !== new URL(fallback, window.location.href).href) {
          image.src = fallback;
        }
      };
      image.src = imageUrl(product.slug);
      image.alt = product.name + ' product image';
      name.textContent = product.name;
      category.textContent = product.category;
    };

    if (animate) {
      slideshow.classList.remove('is-visible');
      setTimeout(() => {
        apply();
        slideshow.classList.add('is-visible');
      }, 180);
    } else {
      apply();
      slideshow.classList.add('is-visible');
    }
  };

  const nextProduct = () => {
    if (!products.length || busy) return;
    busy = true;
    position++;
    if (position >= order.length) {
      order = shuffle(products);
      position = 0;
    }
    showProduct(order[position]);
    setTimeout(() => { busy = false; }, 220);
  };

  const previousProduct = () => {
    if (!products.length || busy) return;
    busy = true;
    position--;
    if (position < 0) {
      position = order.length - 1;
    }
    showProduct(order[position]);
    setTimeout(() => { busy = false; }, 220);
  };

  const startTimer = () => {
    if (timer) clearInterval(timer);
    timer = setInterval(nextProduct, 10000);
  };

  const loadProducts = async () => {
    try {
      const response = await fetch('/products/product-detail.html', {cache:'no-store'});
      if (!response.ok) throw new Error('Could not load product list');
      const html = await response.text();
      const matches = [...html.matchAll(/{"slug":"([^"]+)","name":"([^"]+)","category":"([^"]+)"}/g)];
      products = matches.map(match => ({
        slug: match[1],
        name: match[2],
        category: match[3]
      }));

      if (!products.length) throw new Error('No products found');
    } catch (error) {
      console.warn('Product slideshow could not load the catalogue.', error);
      products = fallbackProducts;
    }

    order = shuffle(products);
    position = 0;
    showProduct(order[position], false);
    startTimer();
  };

  next?.addEventListener('click', () => {
    nextProduct();
    startTimer();
  });

  prev?.addEventListener('click', () => {
    previousProduct();
    startTimer();
  });

  slideshow.addEventListener('mouseenter', () => {
    if (timer) clearInterval(timer);
  });
  slideshow.addEventListener('mouseleave', startTimer);

  loadProducts();
})();
