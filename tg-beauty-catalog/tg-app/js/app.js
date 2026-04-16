/**
 * app.js — Главный файл приложения
 * Содержит: навигацию, рендеринг всех экранов, интеграцию с Telegram SDK.
 * Архитектура: объекты Router, Screens, Components + инициализация App.
 */

'use strict';

// ════════════════════════════════════════════════════════════════════════════
// TELEGRAM SDK — инициализация с заглушкой для браузера
// ════════════════════════════════════════════════════════════════════════════

const tg = (function () {
  if (window.Telegram && window.Telegram.WebApp) {
    return window.Telegram.WebApp;
  }
  // Заглушка для разработки в браузере (не Telegram)
  console.warn('[TgApp] Telegram WebApp SDK не найден — используем заглушку.');
  return {
    themeParams: {},
    colorScheme: 'light',
    MainButton: {
      text: '',
      isVisible: false,
      isActive: true,
      setText(t) { this.text = t; this._update(); },
      show()    { this.isVisible = true;  this._update(); },
      hide()    { this.isVisible = false; this._update(); },
      enable()  { this.isActive = true;  this._update(); },
      disable() { this.isActive = false; this._update(); },
      onClick(fn)  { this._cb = fn; },
      offClick(fn) { this._cb = null; },
      _cb: null,
      _el: null,
      _update() {
        if (!this._el) {
          this._el = document.getElementById('browser-main-btn');
        }
        if (!this._el) return;
        this._el.style.display = this.isVisible ? 'flex' : 'none';
        this._el.textContent = this.text;
        this._el.disabled = !this.isActive;
        this._el.onclick = () => this._cb && this._cb();
      }
    },
    BackButton: {
      isVisible: false,
      show()   { this.isVisible = true;  document.getElementById('browser-back-btn')?.style.setProperty('display','flex'); },
      hide()   { this.isVisible = false; document.getElementById('browser-back-btn')?.style.setProperty('display','none'); },
      onClick(fn)  { this._cb = fn; },
      offClick(fn) { this._cb = null; },
      _cb: null
    },
    HapticFeedback: {
      selectionChanged()           { /* заглушка */ },
      notificationOccurred(type)   { /* заглушка */ },
      impactOccurred(style)        { /* заглушка */ }
    },
    CloudStorage: {
      _store: {},
      setItem(key, val, cb) { this._store[key] = val; cb && cb(null, true); },
      getItem(key, cb)      { cb && cb(null, this._store[key] || null); },
      removeItem(key, cb)   { delete this._store[key]; cb && cb(null, true); }
    },
    showConfirm(msg, cb) {
      const ok = window.confirm(msg);
      cb(ok);
    },
    showAlert(msg, cb) {
      window.alert(msg);
      cb && cb();
    },
    requestContact() { /* заглушка */ },
    enableClosingConfirmation()  { /* заглушка */ },
    disableClosingConfirmation() { /* заглушка */ },
    disableVerticalSwipes()      { /* заглушка */ },
    enableVerticalSwipes()       { /* заглушка */ },
    ready()  { /* заглушка */ },
    expand() { /* заглушка */ },
    close()  { /* заглушка */ },
    initDataUnsafe: {
      user: { first_name: 'Тест', last_name: 'Пользователь', id: 123456 }
    }
  };
})();

// ════════════════════════════════════════════════════════════════════════════
// СОСТОЯНИЕ ПРИЛОЖЕНИЯ
// ════════════════════════════════════════════════════════════════════════════

const State = {
  tab:    'home',      // Активный таб: home | catalog | bookings | about
  screen: 'home',      // Текущий экран
  stack:  [],          // Стек навигации (для кнопки назад)
  params: {},          // Параметры текущего экрана

  // Данные записи (заполняются по шагам)
  booking: {
    service:  null,    // объект услуги
    date:     null,    // строка YYYY-MM-DD
    dateText: null,    // читаемый текст даты
    time:     null,    // строка HH:MM
    phone:    '',      // телефон
    comment:  ''       // комментарий
  },

  // Сохранённые записи (в LocalStorage)
  myBookings: [],

  // Каталог: активная категория
  catalogFilter: 'all',

  // Портфолио: активная категория
  portfolioFilter: 'all',

  // Галерея в детали услуги: текущий слайд
  gallerySlide: 0,

  // Полноэкранный просмотр фото
  viewerOpen: false,
  viewerItems: [],
  viewerIndex: 0
};

// ════════════════════════════════════════════════════════════════════════════
// УТИЛИТЫ
// ════════════════════════════════════════════════════════════════════════════

const Utils = {
  // Форматирует цену: 1500 → "1 500 ₽"
  price(n) {
    return n.toLocaleString('ru-RU') + ' ₽';
  },

  // Форматирует дату: объект Date → "Вт, 15 апреля"
  formatDate(date) {
    if (!date) return '';
    const d = typeof date === 'string' ? new Date(date) : date;
    const days  = ['Вс','Пн','Вт','Ср','Чт','Пт','Сб'];
    const months = ['января','февраля','марта','апреля','мая','июня',
                    'июля','августа','сентября','октября','ноября','декабря'];
    return `${days[d.getDay()]}, ${d.getDate()} ${months[d.getMonth()]}`;
  },

  // Парсит YYYY-MM-DD в Date (без смещения таймзоны)
  parseDate(str) {
    const [y, m, d] = str.split('-').map(Number);
    return new Date(y, m - 1, d);
  },

  // Генерирует строку звёзд: 5 → "★★★★★"
  stars(n) {
    return '★'.repeat(n) + '☆'.repeat(5 - n);
  },

  // Проверяет, занят ли целый день (все слоты заняты)
  isDayUnavailable(dateStr) {
    const busy = APP_DATA.busySlots[dateStr] || [];
    return busy.length >= APP_DATA.timeSlots.length;
  },

  // Возвращает свободные слоты для даты
  getAvailableSlots(dateStr) {
    const busy = APP_DATA.busySlots[dateStr] || [];
    return APP_DATA.timeSlots.map(t => ({
      time: t,
      busy: busy.includes(t)
    }));
  },

  // Безопасный innerHTML через DOMParser
  html(strings, ...vals) {
    let result = '';
    strings.forEach((s, i) => {
      result += s;
      if (i < vals.length) {
        const v = vals[i];
        result += typeof v === 'string' ? v : (v ?? '');
      }
    });
    return result;
  },

  // Escapes HTML entities
  esc(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  },

  // Сохраняет записи в LocalStorage
  saveBookings() {
    try {
      localStorage.setItem('tg_beauty_bookings', JSON.stringify(State.myBookings));
    } catch(e) { /* игнорируем */ }
  },

  // Загружает записи из LocalStorage
  loadBookings() {
    try {
      const raw = localStorage.getItem('tg_beauty_bookings');
      return raw ? JSON.parse(raw) : [];
    } catch(e) { return []; }
  }
};

// ════════════════════════════════════════════════════════════════════════════
// НАВИГАЦИЯ
// ════════════════════════════════════════════════════════════════════════════

const Router = {
  // Переход на новый экран (с анимацией push — справа)
  push(screen, params = {}) {
    State.stack.push({ screen: State.screen, params: State.params });
    this._goto(screen, params, 'push');
  },

  // Вернуться назад (с анимацией pop — слева)
  pop() {
    if (State.stack.length === 0) return;
    const prev = State.stack.pop();
    this._goto(prev.screen, prev.params, 'pop');
  },

  // Переключить таб (fade)
  tab(tabName) {
    State.stack = []; // сбрасываем стек при смене таба
    State.tab = tabName;
    const screenMap = { catalog: 'catalog', about: 'about', portfolio: 'portfolio', bookings: 'myBookings' };
    this._goto(screenMap[tabName], {}, 'tab');
    this._updateTabBar(tabName);
  },

  // Основной метод смены экрана
  _goto(screenName, params, direction) {
    const container   = document.getElementById('screens');
    const oldScreen   = container.querySelector('.screen');
    const html        = Screens[screenName](params);

    // Создаём новый экран
    const newEl = document.createElement('div');
    newEl.className = 'screen';
    newEl.innerHTML = html;

    // Классы анимации
    if (direction === 'push') {
      newEl.classList.add('anim-push-enter');
      if (oldScreen) oldScreen.classList.add('anim-push-leave');
    } else if (direction === 'pop') {
      newEl.classList.add('anim-pop-enter');
      if (oldScreen) oldScreen.classList.add('anim-pop-leave');
    } else {
      newEl.classList.add('anim-tab-enter');
    }

    container.appendChild(newEl);

    // Удаляем старый экран после анимации
    if (oldScreen) {
      setTimeout(() => oldScreen.remove(), 260);
    }

    // Обновляем состояние
    State.screen = screenName;
    State.params = params;

    // Обновляем кнопки Telegram
    this._updateTgButtons(screenName);

    // Управление таббаром
    this._updateTabBarVisibility(screenName);

    // Привязываем события нового экрана
    setTimeout(() => {
      Events.bind(screenName, params, newEl);
    }, 10);
  },

  // Обновляем активный таб в панели
  _updateTabBar(activeTab) {
    document.querySelectorAll('.tab-item').forEach(el => {
      el.classList.toggle('active', el.dataset.tab === activeTab);
    });
  },

  // Показываем/прячем таббар
  _updateTabBarVisibility(screen) {
    const tabScreens = ['catalog', 'myBookings', 'about', 'portfolio'];
    const tabBar     = document.getElementById('tab-bar');
    const isTabScreen = tabScreens.includes(screen);
    tabBar.classList.toggle('hidden', !isTabScreen);

    // Паддинг снизу для контента
    const paddingBottom = isTabScreen ? '64px' : '0px';
    document.documentElement.style.setProperty('--screen-padding-bottom', paddingBottom);
  },

  // Управляем MainButton и BackButton Telegram
  _updateTgButtons(screen) {
    const mb = tg.MainButton;
    const bb = tg.BackButton;

    // Всегда чистим обработчики
    mb.offClick(Events._mainBtnHandler);
    bb.offClick(Events._backBtnHandler);

    switch (screen) {
      case 'serviceDetail':
        mb.setText('Записаться');
        mb.enable();
        mb.show();
        Events._mainBtnHandler = () => Router.push('bookingDateTime', State.params);
        mb.onClick(Events._mainBtnHandler);
        bb.show();
        Events._backBtnHandler = () => Router.pop();
        bb.onClick(Events._backBtnHandler);
        break;

      case 'bookingDateTime':
        mb.setText('Продолжить');
        // Восстанавливаем состояние кнопки (например, при навигации по месяцам)
        if (State.booking.date && State.booking.time) mb.enable();
        else mb.disable();
        mb.show();
        Events._mainBtnHandler = () => {
          if (State.booking.date && State.booking.time) {
            tg.disableVerticalSwipes && tg.disableVerticalSwipes();
            Router.push('bookingConfirm', {});
          }
        };
        mb.onClick(Events._mainBtnHandler);
        bb.show();
        Events._backBtnHandler = () => Router.pop();
        bb.onClick(Events._backBtnHandler);
        break;

      case 'bookingConfirm':
        mb.setText('Подтвердить запись');
        mb.enable();
        mb.show();
        Events._mainBtnHandler = () => Events.submitBooking();
        mb.onClick(Events._mainBtnHandler);
        bb.show();
        Events._backBtnHandler = () => Router.pop();
        bb.onClick(Events._backBtnHandler);
        break;

      case 'bookingSuccess':
        mb.setText('В каталог');
        mb.enable();
        mb.show();
        tg.enableVerticalSwipes && tg.enableVerticalSwipes();
        tg.disableClosingConfirmation && tg.disableClosingConfirmation();
        Events._mainBtnHandler = () => {
          State.stack = [];
          Router.tab('catalog');
        };
        mb.onClick(Events._mainBtnHandler);
        bb.hide();
        break;

      case 'myBookings':
        // Кнопка "Записаться" видна всегда — ведёт в каталог для начала новой записи
        mb.setText('Записаться на приём');
        mb.enable();
        mb.show();
        Events._mainBtnHandler = () => Router.tab('catalog');
        mb.onClick(Events._mainBtnHandler);
        bb.hide();
        break;

      case 'about':
        mb.setText('Записаться');
        mb.enable();
        mb.show();
        Events._mainBtnHandler = () => Router.tab('catalog');
        mb.onClick(Events._mainBtnHandler);
        bb.hide();
        break;

      case 'portfolio':
        // Portfolio теперь таб — без BackButton, без MainButton
        mb.hide();
        bb.hide();
        break;

      case 'reviews':
        mb.hide();
        bb.show();
        Events._backBtnHandler = () => Router.pop();
        bb.onClick(Events._backBtnHandler);
        break;

      default:
        // Главная, каталог — без MainButton, без BackButton
        mb.hide();
        bb.hide();
        break;
    }
  }
};

// ════════════════════════════════════════════════════════════════════════════
// КОМПОНЕНТЫ (переиспользуемые фрагменты HTML)
// ════════════════════════════════════════════════════════════════════════════

const Components = {
  // Фото услуги — img если есть imageUrl, иначе div с градиентом
  photoPlaceholder(item) {
    if (item && item.imageUrl) {
      return `<img src="${item.imageUrl}" alt="" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block;">`;
    }
    const gradient = (item && typeof item === 'object') ? (item.photoGradient || item.grad || '') : (item || '');
    return `<div class="service-card__photo-placeholder"
      style="background:${gradient};display:flex;align-items:flex-end;
             justify-content:flex-start;padding:8px;"></div>`;
  },

  // Карточка услуги
  serviceCard(service, extraData = '') {
    return `
      <div class="service-card" data-action="service-detail" data-id="${service.id}" ${extraData}>
        <div class="service-card__photo">
          ${Components.photoPlaceholder(service)}
        </div>
        <div class="service-card__body">
          <div class="service-card__name">${Utils.esc(service.name)}</div>
          <div class="service-card__meta">
            <span class="service-card__price">${Utils.price(service.price)}</span>
            <span class="service-card__dot">·</span>
            <span class="service-card__duration">${Utils.esc(service.duration)}</span>
          </div>
        </div>
      </div>`;
  },

  // Карточка отзыва
  reviewCard(review) {
    return `
      <div class="review-card">
        <div class="review-card-head">
          <span class="review-card-name">${Utils.esc(review.name)}</span>
          <span class="review-card-stars">${Utils.stars(review.rating)}</span>
        </div>
        <div class="review-card-service">${Utils.esc(review.service)} · ${Utils.esc(review.date)}</div>
        <div class="review-card-text">${Utils.esc(review.text)}</div>
      </div>`;
  },

  // Ячейка портфолио
  portfolioItem(item) {
    const inner = item.imageUrl
      ? `<img src="${item.imageUrl}" alt="${Utils.esc(item.label)}" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block;">`
      : '';
    const bgStyle = item.imageUrl ? '' : `style="background:${item.grad};"`;
    return `
      <div class="portfolio-item" data-action="open-photo" data-id="${item.id}" ${bgStyle}>
        ${inner}
      </div>`;
  },

  // Шаговый индикатор
  stepIndicator(current, total) {
    let dots = '';
    for (let i = 1; i <= total; i++) {
      dots += `<div class="step-dot ${i === current ? 'active' : ''}"></div>`;
    }
    return `<div class="step-indicator">${dots}</div>`;
  },

  // Пустое состояние
  emptyState(icon, title, sub, btnText = null, btnAction = null) {
    const btn = btnText
      ? `<button class="btn btn-primary" ${btnAction ? `data-action="${btnAction}"` : ''}>${btnText}</button>`
      : '';
    return `
      <div class="empty-state">
        <div class="empty-state-icon">${icon}</div>
        <div class="empty-state-title">${title}</div>
        <div class="empty-state-sub">${sub}</div>
        ${btn}
      </div>`;
  }
};

// ════════════════════════════════════════════════════════════════════════════
// ЭКРАНЫ
// ════════════════════════════════════════════════════════════════════════════

const Screens = {

  // ── Экран 1: Главная ──────────────────────────────────────────────────────
  home() {
    const { master } = APP_DATA;
    const popular = APP_DATA.services.filter(s => s.popular);

    const workItems = APP_DATA.portfolio.slice(0, 6).map(item => {
      const bgStyle = item.imageUrl ? '' : `style="background:${item.grad};"`;
      const inner = item.imageUrl ? `<img src="${item.imageUrl}" alt="${Utils.esc(item.label)}" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block;">` : '';
      return `<div class="work-thumb" data-action="open-photo" data-id="${item.id}" ${bgStyle}>${inner}</div>`;
    }).join('');

    const catChips = APP_DATA.categories.map(c => `
      <div class="chip" data-action="go-catalog-cat" data-cat="${Utils.esc(c)}">${Utils.esc(c)}</div>`).join('');

    const popularCards = popular.map(s => Components.serviceCard(s)).join('');

    return `
      <!-- Шапка с мастером -->
      <div class="home-header">
        <div class="master-avatar">${Utils.esc(master.initials)}</div>
        <div class="master-info">
          <div class="master-name">${Utils.esc(master.name)}</div>
          <div class="master-specialty">${Utils.esc(master.specialty)} · ${Utils.esc(master.city)}</div>
        </div>
      </div>

      <!-- Баннер акции -->
      <div class="banner" data-action="go-catalog">
        <div class="banner-deco"></div>
        <div class="banner-deco-2"></div>
        <div class="banner-content">
          <div class="banner-tag">Апрель 2026</div>
          <div class="banner-title">Запись открыта!</div>
          <div class="banner-sub">−20% на первое посещение</div>
        </div>
      </div>

      <!-- Мои работы -->
      <div class="section-header">
        <h2>Мои работы</h2>
        <button class="see-all" data-action="go-portfolio">Все →</button>
      </div>
      <div class="works-scroll">${workItems}</div>

      <!-- Категории -->
      <div class="section-header">
        <h2>Услуги</h2>
      </div>
      <div class="home-cats">${catChips}</div>

      <!-- Популярное -->
      <div class="section-header">
        <h2>Популярное</h2>
      </div>
      <div class="popular-cards screen-padded-bottom">${popularCards}</div>
    `;
  },

  // ── Экран 2: Каталог ─────────────────────────────────────────────────────
  catalog(params = {}) {
    const filter = params.category || State.catalogFilter || 'all';

    const allChip = `<div class="chip ${filter === 'all' ? 'active' : ''}"
      data-action="catalog-filter" data-cat="all">Все</div>`;
    const catChips = APP_DATA.categories.map(c => `
      <div class="chip ${filter === c ? 'active' : ''}"
        data-action="catalog-filter" data-cat="${Utils.esc(c)}">${Utils.esc(c)}</div>`).join('');

    // Группировка услуг по категориям
    let sections = '';
    const grouped = {};
    APP_DATA.services.forEach(s => {
      if (!grouped[s.category]) grouped[s.category] = [];
      grouped[s.category].push(s);
    });

    Object.entries(grouped).forEach(([cat, services]) => {
      if (filter !== 'all' && filter !== cat) return;
      sections += `
        <div class="catalog-section-title" id="cat-${Utils.esc(cat)}">${Utils.esc(cat)}</div>
        ${services.map(s => Components.serviceCard(s)).join('')}
      `;
    });

    return `
      <div class="screen-header">
        <h1>Услуги</h1>
      </div>
      <div class="chips-scroll">${allChip}${catChips}</div>
      <div class="screen-padded-bottom">${sections}</div>
    `;
  },

  // ── Экран 3: Детали услуги ────────────────────────────────────────────────
  serviceDetail(params) {
    const service = APP_DATA.services.find(s => s.id === params.id);
    if (!service) return '<div class="empty-state"><p>Услуга не найдена</p></div>';

    // Все "фото" услуги — берём до 4 элементов из портфолио той же категории
    const photos = APP_DATA.portfolio
      .filter(p => p.serviceId === service.id || p.category === service.category)
      .slice(0, 4);

    // Основная фото-заглушка (первый слайд = сама услуга)
    const slides = [
      { grad: service.photoGradient, imageUrl: service.imageUrl },
      ...photos.map(p => ({ grad: p.grad, imageUrl: p.imageUrl }))
    ];

    const slidesHtml = slides.map((slide, i) => {
      if (slide.imageUrl) {
        return `<div class="service-gallery-slide" style="transform:translateX(${i * 100}%);overflow:hidden;"><img src="${slide.imageUrl}" alt="" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block;"></div>`;
      }
      return `<div class="service-gallery-slide" style="background:${slide.grad};transform:translateX(${i * 100}%);"></div>`;
    }).join('');

    const dots = slides.length > 1
      ? `<div class="gallery-dots">
           ${slides.map((_, i) => `<div class="gallery-dot ${i === 0 ? 'active' : ''}"></div>`).join('')}
         </div>`
      : '';

    const includesList = service.includes
      .map(item => `<li>${Utils.esc(item)}</li>`)
      .join('');

    // Работы 2x2 для этой категории
    const works = APP_DATA.portfolio
      .filter(p => p.category === service.category)
      .slice(0, 6);

    const worksHtml = works.map(item => {
      const bgStyle = item.imageUrl ? '' : `style="background:${item.grad};"`;
      const inner = item.imageUrl ? `<img src="${item.imageUrl}" alt="${Utils.esc(item.label)}" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block;">` : '';
      return `<div class="work-thumb" data-action="open-photo" data-id="${item.id}" ${bgStyle}>${inner}</div>`;
    }).join('');

    // Сохраняем услугу в State.booking
    State.booking.service = service;

    return `
      <!-- Галерея -->
      <div class="service-gallery" id="service-gallery" data-slides="${slides.length}">
        ${slidesHtml}
        ${dots}
      </div>

      <!-- Тело -->
      <div class="service-detail-body">
        <div class="service-detail-title">${Utils.esc(service.name)}</div>
        <div class="service-detail-meta">
          <div class="service-detail-price">${Utils.price(service.price)}</div>
          <div class="service-detail-duration">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
            ${Utils.esc(service.duration)}
          </div>
        </div>

        <div style="margin-bottom:16px;">
          <div class="section-header" style="padding:0 0 8px;">
            <h2 style="font-size:15px;">Что входит:</h2>
          </div>
          <ul class="includes-list">${includesList}</ul>
        </div>

        <button class="btn btn-primary btn-full" data-action="go-booking" style="margin-bottom:24px;">
          Записаться
        </button>

        <div style="margin-bottom:8px;">
          <div class="section-header" style="padding:0 0 8px;">
            <h2 style="font-size:15px;">Работы по услуге</h2>
          </div>
        </div>
      </div>

      <!-- Сетка работ -->
      <div class="service-works-grid screen-padded-bottom">${worksHtml}</div>
    `;
  },

  // ── Экран 4: Выбор даты/времени ──────────────────────────────────────────
  bookingDateTime() {
    const service = State.booking.service;
    const today   = new Date();
    today.setHours(0, 0, 0, 0);

    // Если дата не выбрана — сбрасываем вид на текущий месяц
    // (важно при повторном входе после навигации по месяцам)
    if (!State.booking.date) {
      State.calendarViewDate = new Date(today.getFullYear(), today.getMonth(), 1);
    }
    const viewDate = State.calendarViewDate || new Date(today.getFullYear(), today.getMonth(), 1);
    State.calendarViewDate = viewDate;

    const calendarHtml = this._renderCalendar(viewDate, today);

    const slotsHtml = State.booking.date
      ? this._renderTimeSlots(State.booking.date)
      : `<div class="time-slots-empty">Выберите дату для просмотра доступного времени</div>`;

    return `
      <div class="screen-header">
        <button class="btn-back" data-action="back">
          <svg width="10" height="16" viewBox="0 0 10 16" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="9 1 1 8 9 15"/>
          </svg>
          Назад
        </button>
        <h1>Выбор времени</h1>
        ${Components.stepIndicator(1, 2)}
      </div>

      <!-- Напоминание об услуге -->
      <div class="booking-reminder">
        <div class="rem-name">${service ? Utils.esc(service.name) : '—'}</div>
        <div class="rem-meta">${service ? Utils.price(service.price) + ' · ' + Utils.esc(service.duration) : ''}</div>
      </div>

      <!-- Календарь -->
      ${calendarHtml}

      <!-- Слоты -->
      <div class="time-slots-label">Доступное время</div>
      <div id="time-slots-container">${slotsHtml}</div>
      <div style="height:80px;"></div>
    `;
  },

  // Рендерит HTML календаря
  _renderCalendar(viewDate, today) {
    const MONTHS = ['Январь','Февраль','Март','Апрель','Май','Июнь',
                    'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
    const DAY_NAMES = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];

    const year  = viewDate.getFullYear();
    const month = viewDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay  = new Date(year, month + 1, 0);

    // Первый день недели (0=Вс → 6, 1=Пн → 0, ...)
    let startOffset = firstDay.getDay() - 1;
    if (startOffset < 0) startOffset = 6;

    let cells = '';

    // Пустые ячейки до первого числа
    for (let i = 0; i < startOffset; i++) {
      cells += `<div class="calendar-day disabled"></div>`;
    }

    // Дни месяца
    for (let d = 1; d <= lastDay.getDate(); d++) {
      const date    = new Date(year, month, d);
      const dateStr = `${year}-${String(month + 1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
      const isPast  = date < today;
      const isToday = date.getTime() === today.getTime();
      const isUnavail = !isPast && Utils.isDayUnavailable(dateStr);
      const isSelected = State.booking.date === dateStr;

      let cls = 'calendar-day';
      if (isPast)       cls += ' disabled';
      else if (isUnavail) cls += ' unavailable';
      if (isToday)      cls += ' today';
      if (isSelected)   cls += ' selected';

      const action = (!isPast && !isUnavail) ? `data-action="pick-date" data-date="${dateStr}"` : '';

      cells += `<div class="${cls}" ${action}>${d}</div>`;
    }

    const dayNamesHtml = DAY_NAMES.map(n => `<div class="calendar-day-name">${n}</div>`).join('');

    return `
      <div class="calendar">
        <div class="calendar-header">
          <div class="calendar-month">${MONTHS[month]} ${year}</div>
          <div class="calendar-nav">
            <button class="calendar-nav-btn" data-action="cal-prev">
              <svg width="8" height="12" viewBox="0 0 8 12" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="7 1 1 6 7 11"/>
              </svg>
            </button>
            <button class="calendar-nav-btn" data-action="cal-next">
              <svg width="8" height="12" viewBox="0 0 8 12" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="1 1 7 6 1 11"/>
              </svg>
            </button>
          </div>
        </div>
        <div class="calendar-grid">
          ${dayNamesHtml}
          ${cells}
        </div>
      </div>`;
  },

  // Рендерит слоты времени для выбранной даты
  _renderTimeSlots(dateStr) {
    const slots = Utils.getAvailableSlots(dateStr);
    return `
      <div class="time-slots-grid">
        ${slots.map(s => `
          <div class="time-slot ${s.busy ? 'busy' : ''} ${State.booking.time === s.time && !s.busy ? 'selected' : ''}"
               ${!s.busy ? `data-action="pick-time" data-time="${s.time}"` : ''}>
            ${s.time}
          </div>`).join('')}
      </div>`;
  },

  // ── Экран 5: Подтверждение записи ────────────────────────────────────────
  bookingConfirm() {
    const b = State.booking;
    const service = b.service;

    tg.enableClosingConfirmation && tg.enableClosingConfirmation();

    return `
      <div class="screen-header">
        <button class="btn-back" data-action="back">
          <svg width="10" height="16" viewBox="0 0 10 16" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="9 1 1 8 9 15"/>
          </svg>
          Назад
        </button>
        <h1>Подтверждение</h1>
        ${Components.stepIndicator(2, 2)}
      </div>

      <div style="padding: 8px 16px 12px; font-size:20px; font-weight:700; color:var(--text);">
        Ваша запись
      </div>

      <!-- Сводка -->
      <div class="booking-summary-card">
        <div class="booking-summary-row">
          <div class="row-icon">💅</div>
          <div>
            <div class="row-label">Услуга</div>
            <div class="row-value">${service ? Utils.esc(service.name) : '—'}</div>
          </div>
        </div>
        <div class="booking-summary-row">
          <div class="row-icon">📅</div>
          <div>
            <div class="row-label">Дата</div>
            <div class="row-value">${Utils.esc(b.dateText || '—')}</div>
          </div>
        </div>
        <div class="booking-summary-row">
          <div class="row-icon">🕐</div>
          <div>
            <div class="row-label">Время · Длительность</div>
            <div class="row-value">${Utils.esc(b.time || '—')} · ${service ? Utils.esc(service.duration) : ''}</div>
          </div>
        </div>
        <div class="booking-summary-row">
          <div class="row-icon">💰</div>
          <div>
            <div class="row-label">Стоимость</div>
            <div class="row-value">${service ? Utils.price(service.price) : '—'}</div>
          </div>
        </div>
      </div>

      <!-- Телефон -->
      <div class="phone-block">
        <label>Ваш телефон для связи</label>
        <div class="phone-row">
          <input type="tel" id="phone-input" class="phone-input"
            placeholder="+7 (___) ___-__-__"
            value="${Utils.esc(b.phone || '')}" maxlength="18">
          <button class="btn btn-secondary" data-action="request-contact"
            style="flex-shrink:0;padding:0 14px;min-height:44px;font-size:13px;">
            Из TG
          </button>
        </div>
      </div>

      <!-- Комментарий -->
      <div class="comment-block">
        <label>Комментарий (необязательно)</label>
        <textarea id="comment-input" class="comment-textarea"
          placeholder="Пожелания к дизайну, цвету, форме…"
          maxlength="200">${Utils.esc(b.comment || '')}</textarea>
        <div class="char-count" id="char-count">${(b.comment || '').length}/200</div>
      </div>

      <!-- Политика отмены -->
      <div class="cancel-policy">
        <span>ℹ️</span>
        <span>Отмена бесплатна за 24 часа до записи. После — резервируется 50% стоимости.</span>
      </div>

      <div style="height:80px;"></div>
    `;
  },

  // ── Экран 6: Успех ────────────────────────────────────────────────────────
  bookingSuccess() {
    const b = State.booking;
    const service = b.service;

    // Вибрация успеха
    tg.HapticFeedback.notificationOccurred('success');

    return `
      <div class="success-screen screen-padded-bottom">
        <!-- SVG анимированная галочка -->
        <div class="success-animation">
          <svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="48" cy="48" r="46" stroke="#34C759" stroke-width="4"
              class="checkmark-circle"/>
            <path d="M28 48 L42 62 L68 34" stroke="#34C759" stroke-width="5"
              stroke-linecap="round" stroke-linejoin="round"
              class="checkmark-check"/>
          </svg>
        </div>

        <div class="success-title">Вы записаны!</div>
        <div class="success-sub">Ждём вас. Напомним за 24 часа.</div>

        <!-- Карточка записи -->
        <div class="success-card">
          <div class="success-card-row">
            <span class="icon">💅</span>
            <span class="value">${service ? Utils.esc(service.name) : '—'}</span>
          </div>
          <div class="success-card-row">
            <span class="icon">📅</span>
            <span class="value">${Utils.esc(b.dateText || '—')}</span>
          </div>
          <div class="success-card-row">
            <span class="icon">🕐</span>
            <span class="value">${Utils.esc(b.time || '—')} · ${service ? Utils.esc(service.duration) : ''}</span>
          </div>
          <div class="success-card-row">
            <span class="icon">💰</span>
            <span class="value">${service ? Utils.price(service.price) : '—'}</span>
          </div>
        </div>

        <!-- Кнопки действий -->
        <div class="success-actions">
          <button class="btn btn-secondary btn-full" data-action="go-my-bookings">
            В мои записи
          </button>
        </div>
      </div>
    `;
  },

  // ── Экран 7: Мои записи ───────────────────────────────────────────────────
  myBookings(params = {}) {
    const tab = params.tab || 'upcoming';
    const now = new Date();
    now.setHours(0, 0, 0, 0);

    const upcoming = State.myBookings.filter(b => {
      const d = Utils.parseDate(b.date);
      return d >= now;
    });

    const past = State.myBookings.filter(b => {
      const d = Utils.parseDate(b.date);
      return d < now;
    });

    const list = tab === 'upcoming' ? upcoming : past;

    let listHtml = '';
    if (list.length === 0) {
      if (tab === 'upcoming') {
        listHtml = Components.emptyState(
          '📅',
          'Нет предстоящих записей',
          'Запишитесь на удобное время — это займёт меньше минуты.',
          'Перейти к услугам',
          'go-catalog'
        );
      } else {
        listHtml = Components.emptyState(
          '🕐',
          'История пуста',
          'Здесь появятся ваши прошлые посещения.'
        );
      }
    } else {
      listHtml = list.map(b => {
        const service = APP_DATA.services.find(s => s.id === b.serviceId);
        const name = service ? service.name : b.serviceName || 'Услуга';
        const price = service ? Utils.price(service.price) : '';

        if (tab === 'upcoming') {
          return `
            <div class="booking-item">
              <div class="booking-item-head">
                <div class="booking-item-name">${Utils.esc(name)}</div>
                <div class="booking-item-meta">${Utils.esc(b.dateText)} · ${Utils.esc(b.time)}</div>
                <div class="booking-item-price">${price}</div>
              </div>
              <div class="booking-item-actions">
                <button class="booking-action-btn" data-action="reschedule-booking" data-bid="${b.id}">
                  Перенести
                </button>
                <button class="booking-action-btn danger" data-action="cancel-booking" data-bid="${b.id}">
                  Отменить
                </button>
              </div>
            </div>`;
        } else {
          return `
            <div class="booking-item">
              <div class="booking-item-head">
                <div class="booking-item-name">${Utils.esc(name)}</div>
                <div class="booking-item-meta">${Utils.esc(b.dateText)} · ${Utils.esc(b.time)}</div>
                <div class="booking-item-price">${price}</div>
                <div class="booking-badge">✓ Выполнено</div>
              </div>
              <div class="booking-item-actions">
                <button class="booking-action-btn" data-action="rebook" data-sid="${b.serviceId}">
                  Записаться снова
                </button>
              </div>
            </div>`;
        }
      }).join('');
    }

    return `
      <div class="screen-header">
        <h1>Мои записи</h1>
      </div>

      <div class="bookings-tabs">
        <button class="bookings-tab ${tab === 'upcoming' ? 'active' : ''}"
          data-action="bookings-tab" data-tab="upcoming">
          Предстоящие ${upcoming.length > 0 ? `(${upcoming.length})` : ''}
        </button>
        <button class="bookings-tab ${tab === 'past' ? 'active' : ''}"
          data-action="bookings-tab" data-tab="past">
          Прошлые
        </button>
      </div>

      <div id="bookings-list" class="screen-padded-bottom">${listHtml}</div>
    `;
  },

  // ── Экран 8: О мастере ───────────────────────────────────────────────────
  about() {
    const { master } = APP_DATA;
    const topReviews = APP_DATA.reviews.slice(0, 2);
    const portfolioPreview = APP_DATA.portfolio.slice(0, 6);

    const tags = master.tags.map(t =>
      `<div class="tag-pill">${Utils.esc(t)}</div>`
    ).join('');

    const portfolioHtml = portfolioPreview.map(item => {
      const bgStyle = item.imageUrl ? '' : `style="background:${item.grad};"`;
      const inner = item.imageUrl ? `<img src="${item.imageUrl}" alt="${Utils.esc(item.label)}" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block;">` : '';
      return `<div class="portfolio-item" data-action="open-photo" data-id="${item.id}" ${bgStyle}>${inner}</div>`;
    }).join('');

    const reviewsHtml = topReviews.map(r => Components.reviewCard(r)).join('');

    return `
      <!-- Профиль мастера -->
      <div class="about-header">
        <div class="master-avatar large">${Utils.esc(master.initials)}</div>
        <div class="about-name">${Utils.esc(master.name)}</div>
        <div class="about-spec">${Utils.esc(master.specialty)} · ${Utils.esc(master.city)}</div>
        <div class="rating-badge">
          <span class="stars">★</span>
          <span>${master.rating}</span>
          <span style="color:var(--muted);font-weight:400">(${master.reviewsCount} отзывов)</span>
        </div>
      </div>

      <!-- О себе -->
      <div class="section-header">
        <h2>О себе</h2>
      </div>
      <div class="about-bio">${Utils.esc(master.bio)}</div>

      <!-- Специализации -->
      <div class="section-header" style="margin-top:8px;">
        <h2>Специализации</h2>
      </div>
      <div class="tags-row">${tags}</div>

      <!-- Работы -->
      <div class="section-header">
        <h2>Работы</h2>
        <button class="see-all" data-action="go-portfolio">Смотреть все →</button>
      </div>
      <div class="portfolio-grid" style="padding:0 0 8px;">${portfolioHtml}</div>

      <!-- Отзывы -->
      <div class="section-header">
        <h2>Отзывы</h2>
        <button class="see-all" data-action="go-reviews">Все (${master.reviewsCount}) →</button>
      </div>
      ${reviewsHtml}

      <div style="height:80px;"></div>
    `;
  },

  // ── Экран 9: Портфолио ────────────────────────────────────────────────────
  portfolio(params = {}) {
    const filter = params.filter || State.portfolioFilter || 'all';
    State.portfolioFilter = filter;

    const allChip = `<div class="chip ${filter === 'all' ? 'active' : ''}"
      data-action="portfolio-filter" data-cat="all">Все</div>`;
    const catChips = APP_DATA.categories.map(c => `
      <div class="chip ${filter === c ? 'active' : ''}"
        data-action="portfolio-filter" data-cat="${Utils.esc(c)}">${Utils.esc(c)}</div>`
    ).join('');

    const items = filter === 'all'
      ? APP_DATA.portfolio
      : APP_DATA.portfolio.filter(p => p.category === filter);

    const gridHtml = items.map(item => Components.portfolioItem(item)).join('');

    return `
      <div class="screen-header">
        <button class="btn-back" data-action="back">
          <svg width="10" height="16" viewBox="0 0 10 16" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="9 1 1 8 9 15"/>
          </svg>
          Назад
        </button>
        <h1>Работы</h1>
      </div>
      <div class="chips-scroll">${allChip}${catChips}</div>
      <div class="portfolio-grid screen-padded-bottom">${gridHtml}</div>
    `;
  },

  // ── Экран 10: Отзывы ──────────────────────────────────────────────────────
  reviews() {
    const { master } = APP_DATA;
    const breakdown = master.ratingBreakdown; // [5★, 4★, 3★, 2★, 1★]
    const total = breakdown.reduce((a, b) => a + b, 0);

    const barsHtml = breakdown.map((count, i) => {
      const stars = 5 - i;
      const pct   = total > 0 ? Math.round(count / total * 100) : 0;
      return `
        <div class="rating-bar-row">
          <span class="rating-bar-label">${stars}★</span>
          <div class="rating-bar-track">
            <div class="rating-bar-fill" style="width:${pct}%"></div>
          </div>
        </div>`;
    }).join('');

    const reviewsHtml = APP_DATA.reviews.map(r => Components.reviewCard(r)).join('');

    return `
      <div class="screen-header">
        <button class="btn-back" data-action="back">
          <svg width="10" height="16" viewBox="0 0 10 16" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="9 1 1 8 9 15"/>
          </svg>
          Назад
        </button>
        <h1>Отзывы</h1>
      </div>

      <div class="rating-summary">
        <div class="rating-big">
          <div class="num">${master.rating}</div>
          <div class="stars">★★★★★</div>
          <div class="count">${total} отзывов</div>
        </div>
        <div class="rating-bars">${barsHtml}</div>
      </div>

      <div class="screen-padded-bottom">${reviewsHtml}</div>
    `;
  }
};

// ════════════════════════════════════════════════════════════════════════════
// ОБРАБОТЧИКИ СОБЫТИЙ
// ════════════════════════════════════════════════════════════════════════════

const Events = {
  // Хранилище обработчиков Telegram-кнопок (нужно для offClick)
  _mainBtnHandler: null,
  _backBtnHandler:  null,

  // Привязываем события экрана через делегирование
  bind(screenName, params, el) {
    el.addEventListener('click', (e) => {
      const target = e.target.closest('[data-action]');
      if (!target) return;
      this.handleAction(target.dataset.action, target.dataset, e);
    });

    // Специфические обработчики экрана
    if (screenName === 'serviceDetail') {
      this._bindGallery(el);
    }
    if (screenName === 'bookingConfirm') {
      this._bindBookingConfirm(el);
    }
  },

  // Центральный диспетчер действий
  handleAction(action, data, e) {
    e.stopPropagation();

    switch (action) {
      // Навигация
      case 'back':
        Router.pop(); break;

      case 'go-catalog':
        Router.tab('catalog'); break;

      case 'go-catalog-cat':
        State.catalogFilter = data.cat;
        Router.tab('catalog');
        // Небольшая задержка для прокрутки к секции
        setTimeout(() => {
          const el = document.getElementById(`cat-${data.cat}`);
          el && el.scrollIntoView({ behavior: 'smooth' });
        }, 300);
        break;

      case 'go-portfolio':
        Router.tab('portfolio'); break;

      case 'go-reviews':
        Router.push('reviews', {}); break;

      case 'go-my-bookings':
        State.stack = [];
        Router.tab('bookings'); break;

      // Детали услуги
      case 'service-detail':
        Router.push('serviceDetail', { id: Number(data.id) }); break;

      // Каталог
      case 'catalog-filter':
        State.catalogFilter = data.cat;
        Router._goto('catalog', { category: data.cat }, 'tab');
        if (data.cat !== 'all') {
          setTimeout(() => {
            const el = document.getElementById(`cat-${data.cat}`);
            el && el.scrollIntoView({ behavior: 'smooth' });
          }, 100);
        }
        break;

      // Портфолио
      case 'portfolio-filter':
        State.portfolioFilter = data.cat;
        Router._goto('portfolio', { filter: data.cat }, 'tab');
        break;

      // Открыть фото
      case 'open-photo':
        this.openPhotoViewer(Number(data.id)); break;

      // Закрыть просмотр
      case 'close-viewer':
        this.closePhotoViewer(); break;

      // Записаться из просмотра фото
      case 'viewer-book':
        this.closePhotoViewer();
        const photo = APP_DATA.portfolio.find(p => p.id === Number(data.id));
        if (photo) {
          const service = APP_DATA.services.find(s => s.id === photo.serviceId)
            || APP_DATA.services.find(s => s.category === photo.category);
          if (service) {
            Router.push('serviceDetail', { id: service.id });
          }
        }
        break;

      // Календарь
      case 'pick-date':
        this.selectDate(data.date); break;

      case 'cal-prev':
        this.calNav(-1); break;

      case 'cal-next':
        this.calNav(1); break;

      // Слот времени
      case 'pick-time':
        this.selectTime(data.time); break;

      // Запрос контакта
      case 'request-contact':
        tg.requestContact(); break;

      // Мои записи — табы
      case 'bookings-tab':
        Router._goto('myBookings', { tab: data.tab }, 'tab'); break;

      // Отменить запись
      case 'cancel-booking':
        tg.showConfirm('Отменить запись?', (ok) => {
          if (ok) {
            State.myBookings = State.myBookings.filter(b => b.id !== data.bid);
            Utils.saveBookings();
            Router._goto('myBookings', { tab: 'upcoming' }, 'tab');
          }
        }); break;

      // Перенести запись
      case 'reschedule-booking': {
        const booking = State.myBookings.find(b => b.id === data.bid);
        if (booking) {
          const service = APP_DATA.services.find(s => s.id === booking.serviceId);
          if (service) {
            State.booking.service = service;
            State.booking.date = null;
            State.booking.time = null;
            Router.push('bookingDateTime', {});
          }
        }
        break;
      }

      // Записаться снова
      case 'rebook': {
        const service = APP_DATA.services.find(s => s.id === Number(data.sid));
        if (service) {
          State.booking.service = service;
          State.booking.date = null;
          State.booking.time = null;
          Router.push('bookingDateTime', {});
        }
        break;
      }

      case 'go-catalog-from-bookings':
        Router.tab('catalog'); break;

      case 'go-booking':
        Router.push('bookingDateTime', State.params);
        break;
    }
  },

  // ── Галерея в деталях услуги ──────────────────────────────────────────────
  _bindGallery(el) {
    const gallery = el.querySelector('#service-gallery');
    if (!gallery) return;

    let startX = 0;
    let slideCount = parseInt(gallery.dataset.slides) || 1;
    let currentSlide = 0;

    gallery.addEventListener('touchstart', (e) => {
      startX = e.touches[0].clientX;
    }, { passive: true });

    gallery.addEventListener('touchend', (e) => {
      const diff = startX - e.changedTouches[0].clientX;
      if (Math.abs(diff) < 40) return;

      if (diff > 0 && currentSlide < slideCount - 1) currentSlide++;
      else if (diff < 0 && currentSlide > 0) currentSlide--;
      else return;

      tg.HapticFeedback.selectionChanged();
      this._updateGallery(gallery, currentSlide, slideCount);
    }, { passive: true });
  },

  _updateGallery(gallery, slide, total) {
    const slides = gallery.querySelectorAll('.service-gallery-slide');
    slides.forEach((s, i) => {
      s.style.transform = `translateX(${(i - slide) * 100}%)`;
    });
    gallery.querySelectorAll('.gallery-dot').forEach((d, i) => {
      d.classList.toggle('active', i === slide);
    });
  },

  // ── Поля подтверждения записи ─────────────────────────────────────────────
  _bindBookingConfirm(el) {
    const phoneInput   = el.querySelector('#phone-input');
    const commentInput = el.querySelector('#comment-input');
    const charCount    = el.querySelector('#char-count');

    phoneInput && phoneInput.addEventListener('input', (e) => {
      State.booking.phone = e.target.value;
    });

    commentInput && commentInput.addEventListener('input', (e) => {
      State.booking.comment = e.target.value;
      if (charCount) charCount.textContent = e.target.value.length + '/200';
    });
  },

  // ── Выбор даты в календаре ────────────────────────────────────────────────
  selectDate(dateStr) {
    tg.HapticFeedback.selectionChanged();
    State.booking.date     = dateStr;
    State.booking.dateText = Utils.formatDate(dateStr);
    State.booking.time     = null; // сбрасываем выбранное время

    // Перерисовываем только блок с днями и слотами
    const screenEl = document.querySelector('.screen');
    if (!screenEl) return;

    // Обновляем выделение в календаре
    screenEl.querySelectorAll('.calendar-day').forEach(d => {
      d.classList.toggle('selected', d.dataset.date === dateStr);
    });

    // Перерисовываем слоты
    const slotsContainer = document.getElementById('time-slots-container');
    if (slotsContainer) {
      slotsContainer.innerHTML = Screens._renderTimeSlots(dateStr);
      // Автоскролл к слотам, чтобы пользователь сразу их видел
      setTimeout(() => {
        slotsContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 80);
    }

    // Деактивируем MainButton (активируется после выбора времени)
    tg.MainButton.disable();
  },

  // ── Выбор временного слота ────────────────────────────────────────────────
  selectTime(time) {
    tg.HapticFeedback.selectionChanged();
    State.booking.time = time;

    // Обновляем выделение слотов
    document.querySelectorAll('.time-slot').forEach(el => {
      el.classList.toggle('selected', el.dataset.time === time);
    });

    // Активируем MainButton
    tg.MainButton.enable();
  },

  // ── Навигация по месяцам в календаре ─────────────────────────────────────
  calNav(dir) {
    const v = State.calendarViewDate;
    State.calendarViewDate = new Date(v.getFullYear(), v.getMonth() + dir, 1);
    // Перерисовываем весь экран с обновлённым State.calendarViewDate
    Router._goto('bookingDateTime', {}, 'tab');
  },

  // ── Открытие просмотра фото ───────────────────────────────────────────────
  openPhotoViewer(photoId) {
    const photo = APP_DATA.portfolio.find(p => p.id === photoId);
    if (!photo) return;

    // Ищем сервис для этого фото
    const service = APP_DATA.services.find(s => s.id === photo.serviceId)
      || APP_DATA.services.find(s => s.category === photo.category);

    const viewer = document.getElementById('photo-viewer');
    const photoHtml = photo.imageUrl
      ? `<img src="${photo.imageUrl}" alt="${Utils.esc(photo.label)}" style="width:100%;height:60vh;object-fit:cover;display:block;">`
      : `<div style="width:100%;height:60vh;background:${photo.grad};"></div>`;
    viewer.innerHTML = `
      <button class="photo-viewer-close" data-action="close-viewer">✕</button>
      ${photoHtml}
      <div class="photo-viewer-info">
        <div class="photo-name">${Utils.esc(photo.label)}</div>
        <div class="photo-price">${service ? Utils.price(service.price) : ''}</div>
        <button class="photo-viewer-btn" data-action="viewer-book" data-id="${photo.id}">
          Записаться
        </button>
      </div>
    `;
    viewer.classList.remove('hidden');
    // Клики обрабатываются постоянным listener-ом из App.init()
  },

  closePhotoViewer() {
    const viewer = document.getElementById('photo-viewer');
    viewer.classList.add('hidden');
  },

  // ── Отправка записи ───────────────────────────────────────────────────────
  submitBooking() {
    const b = State.booking;

    // Сохраняем запись
    const newBooking = {
      id:          Date.now().toString(),
      serviceId:   b.service?.id,
      serviceName: b.service?.name,
      date:        b.date,
      dateText:    b.dateText,
      time:        b.time,
      phone:       b.phone,
      comment:     b.comment,
      createdAt:   new Date().toISOString()
    };

    State.myBookings.push(newBooking);
    Utils.saveBookings();

    // Сохраняем в CloudStorage (черновик/история)
    tg.CloudStorage.setItem('last_booking', JSON.stringify(newBooking));

    // Переходим на экран успеха
    Router.push('bookingSuccess', {});
  }
};

// ════════════════════════════════════════════════════════════════════════════
// ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ
// ════════════════════════════════════════════════════════════════════════════

const App = {
  init() {
    // Сигнализируем Telegram, что приложение готово
    tg.ready();
    tg.expand();

    // Загружаем сохранённые записи
    State.myBookings = Utils.loadBookings();

    // Применяем тему Telegram
    this.applyTheme();

    // Инициализируем таббар
    this.initTabBar();

    // Постоянный обработчик для photo-viewer (открытие/закрытие)
    this.initPhotoViewer();

    // Рендерим первый экран
    Router.tab('catalog');

    // Слушаем изменение темы Telegram
    if (tg.onEvent) {
      tg.onEvent('themeChanged', () => this.applyTheme());
    }
  },

  initPhotoViewer() {
    const viewer = document.getElementById('photo-viewer');
    viewer.addEventListener('click', (e) => {
      // Тап на фон (не на кнопку) — закрываем
      if (e.target === viewer) {
        Events.closePhotoViewer();
        return;
      }
      const target = e.target.closest('[data-action]');
      if (!target) return;
      Events.handleAction(target.dataset.action, target.dataset, e);
    });
  },

  applyTheme() {
    const isDark = tg.colorScheme === 'dark';
    document.body.classList.toggle('dark-theme', isDark);

    // Если Telegram передаёт свои цвета — применяем их
    const tp = tg.themeParams || {};
    if (tp.bg_color) {
      document.documentElement.style.setProperty('--bg', tp.bg_color);
    }
    if (tp.secondary_bg_color) {
      document.documentElement.style.setProperty('--card', tp.secondary_bg_color);
    }
    if (tp.text_color) {
      document.documentElement.style.setProperty('--text', tp.text_color);
    }
    if (tp.hint_color) {
      document.documentElement.style.setProperty('--muted', tp.hint_color);
    }
    // Акцент #C9967A — брендовый, не перекрываем
  },

  initTabBar() {
    const tabBar = document.getElementById('tab-bar');
    tabBar.addEventListener('click', (e) => {
      const btn = e.target.closest('.tab-item');
      if (!btn) return;
      const tab = btn.dataset.tab;
      if (tab && tab !== State.tab) {
        tg.HapticFeedback.selectionChanged();
        State.tab = tab;
        Router._updateTabBar(tab);
        Router.tab(tab);
      }
    });
  }
};

// Запуск после загрузки DOM
document.addEventListener('DOMContentLoaded', () => App.init());
