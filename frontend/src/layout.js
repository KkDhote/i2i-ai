// Retain explicitly pinned cards (and the last edited card) in their old slots.
export function preserveCards(next, previous, protectedIds) {
  if (!previous) return next;
  const fixed = previous.components.map((card, index) => ({ card, index })).filter(({ card }) => protectedIds.includes(card.id));
  const cards = next.components.filter(card => !fixed.some(item => item.card.id === card.id));
  for (const { card, index } of fixed) cards.splice(Math.min(index, cards.length), 0, card);
  while (cards.length > 10) {
    const removable = cards.findLastIndex(card => !protectedIds.includes(card.id));
    if (removable < 0) break;
    cards.splice(removable, 1);
  }
  return { ...next, components: cards };
}
