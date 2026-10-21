"use strict";
// Яндекс Метрика для всех страниц. Номер счётчика — только здесь; пока 0, скрипт ничего не грузит.
// Вебвизор выключен: он записывал бы текст, который посетитель набирает в чате (ПДн).
(() => {
  const YM_ID = 0;

  const sent = new Set();
  // Цели, которые не должны дублироваться за визит (повтор запроса чата возвращает ту же заявку).
  window.ymGoal = (name, once) => {
    if (!YM_ID || typeof window.ym !== "function") return;
    if (once) { if (sent.has(name)) return; sent.add(name); }
    window.ym(YM_ID, "reachGoal", name);
  };
  if (!YM_ID) return;

  window.ym = window.ym || function () { (window.ym.a = window.ym.a || []).push(arguments); };
  window.ym.l = Date.now();
  const s = document.createElement("script");
  s.async = true;
  s.src = "https://mc.yandex.ru/metrika/tag.js";
  document.head.appendChild(s);
  window.ym(YM_ID, "init", {clickmap: true, trackLinks: true, accurateTrackBounce: true, webvisor: false});

  document.addEventListener("click", (e) => {
    const a = e.target.closest && e.target.closest("a[href]");
    if (!a) return;
    const href = a.getAttribute("href");
    if (href.includes("max.ru/")) window.ymGoal("click_max");
    else if (href.includes("t.me/")) window.ymGoal("click_telegram");
    else if (href.startsWith("mailto:")) window.ymGoal("click_email");
    else if (href.endsWith("#chat")) window.ymGoal("open_chat");
  });

  // Уведомление о cookie: показываем один раз, согласие запоминаем в браузере.
  try { if (localStorage.getItem("cookie-ok")) return; } catch (e) { /* без хранилища показываем каждый раз */ }
  const bar = document.createElement("div");
  bar.setAttribute("role", "region");
  bar.setAttribute("aria-label", "Уведомление о cookie");
  bar.style.cssText = "position:fixed;left:16px;right:16px;bottom:16px;z-index:50;max-width:560px;margin:0 auto;" +
    "display:flex;gap:12px;align-items:center;padding:12px 16px;border-radius:16px;background:#1a1a17;" +
    "color:#e9e6dc;font:14px/1.4 'Golos Text',system-ui,sans-serif;box-shadow:0 8px 32px rgba(0,0,0,.4)";
  bar.innerHTML = '<span style="flex:1">Сайт использует cookie и Яндекс Метрику для статистики посещений. ' +
    '<a href="/privacy.html" style="color:inherit">Подробнее</a></span>' +
    '<button type="button" style="border:0;border-radius:999px;padding:8px 16px;background:#e9e6dc;color:#0f0f0d;font:inherit;cursor:pointer">Понятно</button>';
  bar.querySelector("button").addEventListener("click", () => {
    try { localStorage.setItem("cookie-ok", "1"); } catch (e) { /* не сохранилось — покажем снова */ }
    bar.remove();
  });
  const mount = () => document.body.appendChild(bar);
  if (document.body) mount(); else document.addEventListener("DOMContentLoaded", mount);
})();
