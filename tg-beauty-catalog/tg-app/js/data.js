/**
 * data.js — Все данные приложения
 * Здесь меняешь: услуги, цены, отзывы, данные мастера, слоты времени.
 * Чтобы обновить контент — редактируй только этот файл.
 */

const APP_DATA = {

  // ─── МАСТЕР ───────────────────────────────────────────────────────────────
  master: {
    name:         'Анна Петрова',
    specialty:    'Nail-мастер',
    city:         'Москва',
    rating:       4.9,
    reviewsCount: 84,
    bio:          'Работаю с 2018 года. Специализируюсь на гель-лак, дизайн и наращивании. Люблю сложные работы и нестандартные дизайны. Использую только сертифицированные материалы брендов IRISK и Saga Cosmetics.',
    initials:     'АП',   // для аватара-заглушки
    tags:         ['Гель-лак', 'Наращивание', 'Дизайн', 'Педикюр', 'Брови'],
    // Рейтинговые звёзды (5→1)
    ratingBreakdown: [68, 14, 2, 0, 0]
  },

  // ─── КАТЕГОРИИ ────────────────────────────────────────────────────────────
  categories: ['Маникюр', 'Педикюр', 'Брови', 'Ресницы'],

  // ─── УСЛУГИ ───────────────────────────────────────────────────────────────
  // Поля: id, category, name, price, duration, durationMin, description,
  //       includes (список), popular, photoGradient (для заглушки-фото)
  services: [
    {
      id: 1,
      category: 'Маникюр',
      name: 'Покрытие гель-лак',
      price: 1500,
      duration: '1ч 30м',
      durationMin: 90,
      description: 'Профессиональное покрытие гель-лаком с долгосрочным результатом. Держится 3–4 недели без сколов.',
      includes: [
        'Снятие старого покрытия',
        'Обработка кутикулы',
        'Нанесение базы + гель-лак',
        'Топовое покрытие',
        'Финишная обработка'
      ],
      popular: true,
      photoGradient: 'linear-gradient(135deg, #FFB7C5 0%, #FF8FAB 100%)',
      imageUrl: 'img/service-gel-nails.jpg'
    },
    {
      id: 2,
      category: 'Маникюр',
      name: 'Маникюр + дизайн',
      price: 2200,
      duration: '2ч',
      durationMin: 120,
      description: 'Классический маникюр с художественным дизайном на ваш выбор: минимализм, флористика, градиент, стразы.',
      includes: [
        'Снятие покрытия',
        'Аппаратная обработка кутикулы',
        'Гель-лак (цвет на выбор)',
        'Дизайн до 10 ногтей',
        'Закрепление топом'
      ],
      popular: true,
      photoGradient: 'linear-gradient(135deg, #E8C4B8 0%, #C9967A 100%)',
      imageUrl: 'img/service-nail-design.jpg'
    },
    {
      id: 3,
      category: 'Маникюр',
      name: 'Наращивание на форме',
      price: 3000,
      duration: '2ч 30м',
      durationMin: 150,
      description: 'Наращивание ногтей на форме: квадрат, миндаль, стилет. Покрытие и дизайн по желанию.',
      includes: [
        'Снятие нарощенных (если есть)',
        'Подготовка натурального ногтя',
        'Наращивание гелем на форме',
        'Покрытие гель-лаком',
        'Финишная обработка'
      ],
      popular: false,
      photoGradient: 'linear-gradient(135deg, #C9B8E8 0%, #9B72CF 100%)',
      imageUrl: 'img/service-nail-extension.jpg'
    },
    {
      id: 4,
      category: 'Педикюр',
      name: 'Педикюр с покрытием',
      price: 2000,
      duration: '1ч 30м',
      durationMin: 90,
      description: 'Аппаратный педикюр с полным уходом за стопами и покрытием гель-лаком.',
      includes: [
        'Размягчение стоп',
        'Аппаратная обработка',
        'Удаление мозолей и натоптышей',
        'Обработка кутикулы',
        'Покрытие гель-лаком'
      ],
      popular: true,
      photoGradient: 'linear-gradient(135deg, #B8D4C8 0%, #6BAD99 100%)',
      imageUrl: 'img/service-pedicure.jpg'
    },
    {
      id: 5,
      category: 'Педикюр',
      name: 'Педикюр без покрытия',
      price: 1300,
      duration: '1ч',
      durationMin: 60,
      description: 'Аппаратный педикюр без нанесения покрытия. Только уход и красота стоп.',
      includes: [
        'Размягчение стоп',
        'Аппаратная обработка',
        'Удаление огрублевшей кожи',
        'Обработка кутикулы',
        'Питательное масло для ногтей'
      ],
      popular: false,
      photoGradient: 'linear-gradient(135deg, #C8D4B8 0%, #8FC47B 100%)',
      imageUrl: 'img/service-pedicure-no-cover.jpg'
    },
    {
      id: 6,
      category: 'Брови',
      name: 'Коррекция формы',
      price: 800,
      duration: '30м',
      durationMin: 30,
      description: 'Профессиональная коррекция формы бровей с учётом типа лица. Воском или нитью.',
      includes: [
        'Консультация по форме',
        'Коррекция воском',
        'Доработка пинцетом',
        'Укладка фиксирующим гелем'
      ],
      popular: false,
      photoGradient: 'linear-gradient(135deg, #F5DEB3 0%, #D4A520 100%)',
      imageUrl: 'img/service-eyebrow.jpg'
    },
    {
      id: 7,
      category: 'Брови',
      name: 'Окрашивание + коррекция',
      price: 1200,
      duration: '45м',
      durationMin: 45,
      description: 'Стойкое окрашивание бровей хной + коррекция формы. Держится 2–3 недели.',
      includes: [
        'Подбор оттенка',
        'Коррекция формы',
        'Окрашивание хной',
        'Укладка'
      ],
      popular: false,
      photoGradient: 'linear-gradient(135deg, #D4B8A5 0%, #A07860 100%)',
      imageUrl: 'img/service-eyebrow-color.jpg'
    },
    {
      id: 8,
      category: 'Ресницы',
      name: 'Наращивание ресниц',
      price: 3500,
      duration: '2ч',
      durationMin: 120,
      description: 'Классическое 1D или объёмное 2D/3D наращивание. Натуральный или голливудский эффект.',
      includes: [
        'Консультация',
        'Подбор длины, изгиба и толщины',
        'Наращивание (классика или объём)',
        'Укладка и финальный осмотр'
      ],
      popular: false,
      photoGradient: 'linear-gradient(135deg, #B8C4D4 0%, #6080A8 100%)',
      imageUrl: 'img/service-lash.jpg'
    },
    {
      id: 9,
      category: 'Ресницы',
      name: 'Снятие + коррекция',
      price: 1500,
      duration: '1ч',
      durationMin: 60,
      description: 'Бережное снятие нарощенных ресниц + восстановительный уход + коррекция.',
      includes: [
        'Бережное снятие состав-ремувером',
        'Уход за натуральными ресницами',
        'Лёгкая коррекция (при наличии)',
        'Питательная маска'
      ],
      popular: false,
      photoGradient: 'linear-gradient(135deg, #D4C8E8 0%, #9080C0 100%)',
      imageUrl: 'img/service-lash-fix.jpg'
    }
  ],

  // ─── ОТЗЫВЫ ───────────────────────────────────────────────────────────────
  reviews: [
    {
      id: 1,
      name: 'Мария К.',
      rating: 5,
      service: 'Покрытие гель-лак',
      date: 'Апрель 2026',
      text: 'Очень довольна! Держится уже 3 недели без сколов. Анна — профессионал с большой буквы, всё очень аккуратно и быстро. Буду приходить только сюда!'
    },
    {
      id: 2,
      name: 'Елена В.',
      rating: 5,
      service: 'Наращивание',
      date: 'Март 2026',
      text: 'Анна — лучший мастер! Делала наращивание впервые, очень переживала. Результат превзошёл все ожидания — выглядит очень натурально!'
    },
    {
      id: 3,
      name: 'Юлия Н.',
      rating: 5,
      service: 'Маникюр + дизайн',
      date: 'Март 2026',
      text: 'Обожаю сложные дизайны — Аня всегда воплощает всё, что я придумываю. Записываюсь уже второй год подряд, никуда не уйду!'
    },
    {
      id: 4,
      name: 'Ирина Д.',
      rating: 4,
      service: 'Педикюр с покрытием',
      date: 'Февраль 2026',
      text: 'Хороший педикюр, стопы как после спа. Единственное — пришлось немного подождать, но всё равно очень рекомендую!'
    },
    {
      id: 5,
      name: 'Светлана М.',
      rating: 5,
      service: 'Наращивание ресниц',
      date: 'Апрель 2026',
      text: 'Делаю ресницы только у Ани! Держатся долго, выглядят натурально. Мастер знает своё дело на 100%.'
    },
    {
      id: 6,
      name: 'Татьяна О.',
      rating: 5,
      service: 'Покрытие гель-лак',
      date: 'Апрель 2026',
      text: 'Первый раз была — осталась в полном восторге. Чисто, аккуратно, приятная атмосфера. Уже записалась на следующий раз!'
    },
    {
      id: 7,
      name: 'Кристина Л.',
      rating: 5,
      service: 'Маникюр + дизайн',
      date: 'Январь 2026',
      text: 'Сделала дизайн на новый год — все подруги спрашивают где делала! Анна предложила интересные идеи, я была в восторге.'
    },
    {
      id: 8,
      name: 'Надежда Р.',
      rating: 4,
      service: 'Коррекция формы бровей',
      date: 'Март 2026',
      text: 'Хорошая работа с бровями, форма отличная. Буду возвращаться на коррекцию регулярно.'
    }
  ],

  // ─── ПОРТФОЛИО ────────────────────────────────────────────────────────────
  // Массив "фотографий" работ. Каждое — объект с категорией и градиентом.
  // Чтобы добавить реальные фото: замени photoGradient на imageUrl.
  portfolio: [
    // Маникюр
    { id: 1,  category: 'Маникюр', serviceId: 1, grad: 'linear-gradient(135deg, #FFB7C5, #FF6B9D)', label: 'Розовый гель-лак',   imageUrl: 'img/p1.jpg' },
    { id: 2,  category: 'Маникюр', serviceId: 2, grad: 'linear-gradient(135deg, #FFE0EC, #FFB3CC)', label: 'Nude дизайн',        imageUrl: 'img/p2.jpg' },
    { id: 3,  category: 'Маникюр', serviceId: 2, grad: 'linear-gradient(135deg, #B8E0FF, #7EC8E3)', label: 'Голубой градиент',   imageUrl: 'img/p3.jpg' },
    { id: 4,  category: 'Маникюр', serviceId: 1, grad: 'linear-gradient(135deg, #C9B8E8, #A090D8)', label: 'Лаванда',            imageUrl: 'img/p4.jpg' },
    { id: 5,  category: 'Маникюр', serviceId: 2, grad: 'linear-gradient(135deg, #FFD700, #FFA500)', label: 'Золотой дизайн',     imageUrl: 'img/p5.jpg' },
    { id: 6,  category: 'Маникюр', serviceId: 3, grad: 'linear-gradient(135deg, #FF9A9E, #FECFEF)', label: 'Миндаль rose',       imageUrl: 'img/p6.jpg' },
    { id: 7,  category: 'Маникюр', serviceId: 2, grad: 'linear-gradient(135deg, #A8EDEA, #FED6E3)', label: 'Пастельный микс',    imageUrl: 'img/p7.jpg' },
    { id: 8,  category: 'Маникюр', serviceId: 1, grad: 'linear-gradient(135deg, #2C3E50, #4A5568)', label: 'Классика тёмная',    imageUrl: 'img/p8.jpg' },
    { id: 9,  category: 'Маникюр', serviceId: 3, grad: 'linear-gradient(135deg, #E8C4B8, #C9967A)', label: 'Тёплый nude',        imageUrl: 'img/p9.jpg' },
    // Педикюр
    { id: 10, category: 'Педикюр', serviceId: 4, grad: 'linear-gradient(135deg, #B8D4C8, #6BAD99)', label: 'Педикюр мята',       imageUrl: 'img/p10.jpg' },
    { id: 11, category: 'Педикюр', serviceId: 4, grad: 'linear-gradient(135deg, #FFB7C5, #FF8FAB)', label: 'Педикюр розовый',    imageUrl: 'img/p11.jpg' },
    { id: 12, category: 'Педикюр', serviceId: 5, grad: 'linear-gradient(135deg, #F5DEB3, #DEB887)', label: 'Педикюр бежевый',    imageUrl: 'img/p12.jpg' },
    // Брови
    { id: 13, category: 'Брови',   serviceId: 6, grad: 'linear-gradient(135deg, #D4B896, #A07850)', label: 'Коррекция',          imageUrl: 'img/p13.jpg' },
    { id: 14, category: 'Брови',   serviceId: 7, grad: 'linear-gradient(135deg, #8B7355, #6B5340)', label: 'Окрашивание хной',   imageUrl: 'img/p14.jpg' },
    { id: 15, category: 'Брови',   serviceId: 7, grad: 'linear-gradient(135deg, #C4A882, #9A7855)', label: 'Тёплые брови',       imageUrl: 'img/p15.jpg' },
    // Ресницы
    { id: 16, category: 'Ресницы', serviceId: 8, grad: 'linear-gradient(135deg, #2C2C2C, #4A4A4A)', label: 'Классика 1D',        imageUrl: 'img/p16.jpg' },
    { id: 17, category: 'Ресницы', serviceId: 8, grad: 'linear-gradient(135deg, #3D3D5C, #6B6B9B)', label: 'Объём 3D',           imageUrl: 'img/p17.jpg' },
    { id: 18, category: 'Ресницы', serviceId: 8, grad: 'linear-gradient(135deg, #1A1A2E, #16213E)', label: 'Голливудский',       imageUrl: 'img/p18.jpg' },
  ],

  // ─── РАСПИСАНИЕ ───────────────────────────────────────────────────────────
  // Доступные слоты времени (показываем по умолчанию)
  timeSlots: ['09:00', '10:30', '12:00', '13:30', '15:00', '16:30', '18:00'],

  // Занятые слоты: ключ — дата YYYY-MM-DD, значение — массив занятых времён
  // Если все слоты заняты — день считается недоступным
  busySlots: {
    '2026-04-14': ['09:00', '10:30'],
    '2026-04-15': ['09:00', '12:00', '15:00'],
    '2026-04-16': ['10:30', '13:30'],
    '2026-04-17': ['09:00', '10:30', '12:00', '13:30', '15:00', '16:30', '18:00'],
    '2026-04-18': ['09:00', '16:30', '18:00'],
    '2026-04-19': ['10:30', '15:00', '18:00'],
    '2026-04-21': ['09:00', '10:30', '12:00', '13:30', '15:00', '16:30', '18:00'],
    '2026-04-22': ['09:00', '10:30'],
    '2026-04-24': ['12:00', '13:30', '15:00'],
    '2026-04-28': ['09:00', '10:30', '12:00', '13:30', '15:00', '16:30', '18:00'],
  }
};
