// Scroll a conversation to its end without moving any outer window (e.g. the preview frame).
export const scrollToEnd = (el) => {
  if (!el) return;
  for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
    const { overflowY } = getComputedStyle(p);
    if (/(auto|scroll)/.test(overflowY) && p.scrollHeight > p.clientHeight) {
      p.scrollTo({ top: p.scrollHeight, behavior: "smooth" });
      return;
    }
  }
  window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "smooth" });
};
