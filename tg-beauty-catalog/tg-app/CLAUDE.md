# CLAUDE.md — Документация Telegram Mini App
## tg-beauty-catalog / tg-app

---

## Структура файлов

```
tg-app/
├── index.html          — Точка входа. HTML-оболочка, подключает SDK и скрипты.
├── CLAUDE.md           — Этот файл. Документация проекта.
│
├── css/
│   └── styles.css      — Все стили. CSS-переменные, темы, компоненты.
│
└── js/
    ├── data.js         — ВСЕ ДАННЫЕ. Здесь меняешь цены, услуги, отзывы.
    └── app.js          — Логика приложения: навигация, экраны, события.
```

---

## Где менять контент

### Данные мастера
**Файл:** `js/data.js` → объект `APP_DATA.master`

```javascript
master: {
  name:     'Анна Петрова',    // Имя (отображается везде)
  specialty: 'Nail-мастер',   // Специализация
  city:     'Москва',
  rating:   4.9,
  reviewsCount: 84,
  bio:      'Текст о себе...',
  initials: 'АП',              // Аватар-заглушка (2 буквы)
  tags:     ['Гель-лак', ...]  // Теги-специализации
}
```

### Услуги и цены
**Файл:** `js/data.js` → массив `APP_DATA.services`

Каждая услуга:
```javascript
{
  id:           1,
  category:     'Маникюр',        // Должна совпасть с categories[]
  name:         'Покрытие гель-лак',
  price:        1500,             // В рублях (без ₽)
  duration:     '1ч 30м',        // Текст для отображения
  durationMin:  90,               // Минуты (для расчётов)
  description:  'Текст...',
  includes:     ['Пункт 1', ...], // Что входит (список)
  popular:      true,             // true → показывается на Главной
  photoGradient: 'linear-gradient(...)' // CSS-градиент вместо фото
}
```

### Отзывы
**Файл:** `js/data.js` → массив `APP_DATA.reviews`

### Портфолио (фото-работы)
**Файл:** `js/data.js` → массив `APP_DATA.portfolio`

Чтобы добавить реальные фото вместо градиентов:
1. Положи фото в `tg-app/img/` (формат WebP рекомендуется)
2. В `data.js` вместо `grad: 'linear-gradient(...)'` → добавь `imageUrl: 'img/photo1.webp'`
3. В `app.js` → функция `Components.portfolioItem()` → добавь `<img>` вместо background

### Расписание (занятые слоты)
**Файл:** `js/data.js` → `APP_DATA.busySlots`

```javascript
busySlots: {
  '2026-04-17': ['09:00', '10:30', '12:00', '13:30', '15:00', '16:30', '18:00'],
  // Если все 7 слотов заняты → день помечается как недоступный
}
```

Время слотов: `APP_DATA.timeSlots` — массив строк `['09:00', '10:30', ...]`

---

## Навигация между экранами

```
TAB BAR (постоянная нижняя панель)
  ├── [Главная]   → Screens.home()
  ├── [Услуги]    → Screens.catalog()
  ├── [Записи]    → Screens.myBookings()
  └── [Мастер]   → Screens.about()

Переходы из экранов:
  Главная → тап на карточку     → serviceDetail(id)
  Главная → тап на категорию   → catalog(filter: category)
  Главная → тап "Все →"        → portfolio()
  Каталог → тап на карточку    → serviceDetail(id)
  serviceDetail → [Записаться] → bookingDateTime()
  bookingDateTime → [Продолжить] → bookingConfirm()
  bookingConfirm → [Подтвердить] → bookingSuccess()
  bookingSuccess → [В мои записи] → myBookings()
  bookingSuccess → [На главную]   → home() (через tab)
  about → тап на работу         → portfolio()
  about → "Все отзывы →"        → reviews()
  about → [Записаться]          → catalog()
```

### Стек навигации (кнопка Назад)
- `Router.push(screen, params)` — добавляет экран в стек, анимация вправо
- `Router.pop()` — возвращает предыдущий экран, анимация влево
- `Router.tab(tabName)` — переключает таб, сбрасывает стек, fade-анимация

---

## Архитектура кода (app.js)

```
App          — инициализация, тема, таббар
Router       — вся навигация (push/pop/tab + Telegram buttons)
State        — глобальное состояние приложения
Screens      — функции рендеринга экранов (возвращают HTML-строки)
Components   — переиспользуемые HTML-фрагменты
Events       — обработчики действий (event delegation)
Utils        — вспомогательные функции (форматирование, хранилище)
```

---

## Telegram SDK — что используется

| API | Где | Для чего |
|-----|-----|----------|
| `tg.ready()` | App.init | Сигнал готовности |
| `tg.expand()` | App.init | Полноэкранный режим |
| `tg.MainButton` | Router._updateTgButtons | CTA-кнопки на шагах |
| `tg.BackButton` | Router._updateTgButtons | Кнопка назад |
| `tg.HapticFeedback` | Events.selectDate/Time | Тактильный отклик |
| `tg.CloudStorage` | Events.submitBooking | Сохранение брони |
| `tg.showConfirm()` | Events.cancel-booking | Диалог отмены |
| `tg.requestContact()` | bookingConfirm | Получить телефон |
| `tg.enableClosingConfirmation()` | bookingConfirm | Защита от случайного закрытия |
| `tg.themeParams` | App.applyTheme | Цвета темы Telegram |
| `tg.colorScheme` | App.applyTheme | Светлая/тёмная тема |

---

## Тёмная тема

Автоматически определяется из `tg.colorScheme`.

CSS-переменные тёмной темы описаны в `styles.css` → `.dark-theme {}`.

Брендовый акцент `#C9967A` не перекрывается темой.

---

## Как запустить для разработки

1. Открыть `tg-app/index.html` в браузере (двойной клик или Live Server в VS Code)
2. Приложение работает и в браузере (SDK-заглушка заменяет Telegram API)
3. MainButton появляется как кнопка внизу экрана (`#browser-main-btn`)
4. BackButton — кнопка `‹` в левом верхнем углу (`#browser-back-btn`)

### Для запуска в Telegram:
1. Создай бота через @BotFather
2. Подключи Mini App: `/newapp` → загрузи или укажи URL с `index.html`
3. HTTPS обязателен для работы SDK (используй ngrok/localtunnel для локала)

---

## Добавление новых экранов

1. Добавь функцию в объект `Screens` в `app.js`:
   ```javascript
   myNewScreen(params) {
     return `<div>HTML экрана</div>`;
   }
   ```
2. Зарегистрируй Telegram-кнопки в `Router._updateTgButtons()` (новый `case`)
3. Добавь action в `Events.handleAction()` для кнопки перехода

---

## Полный список экранов

| ID | Имя функции | Таб | Описание |
|----|-------------|-----|----------|
| 1  | `home` | Главная | Главная, баннер, категории, популярное |
| 2  | `catalog` | Услуги | Каталог с фильтрами по категориям |
| 3  | `serviceDetail` | — | Детали услуги, галерея, "Записаться" |
| 4  | `bookingDateTime` | — | Выбор даты (календарь) и времени (слоты) |
| 5  | `bookingConfirm` | — | Подтверждение: сводка, телефон, комментарий |
| 6  | `bookingSuccess` | — | Успешная запись, CSS-анимация галочки |
| 7  | `myBookings` | Записи | Предстоящие и прошлые записи, отмена |
| 8  | `about` | Мастер | Профиль, специализации, работы, отзывы |
| 9  | `portfolio` | — | Галерея работ 3-колонки + просмотр |
| 10 | `reviews` | — | Отзывы с рейтинговыми барами |
