from treys import Card, Deck, Evaluator

print("=== Criação do baralho ===")
deck = Deck()
print(f"Total de cartas: {len(deck.cards)}")

print("\n=== Sorteio de mãos ===")
hand1 = [deck.draw(1)[0], deck.draw(1)[0]]
hand2 = [deck.draw(1)[0], deck.draw(1)[0]]

print("Mão 1:")
Card.print_pretty_cards(hand1)

print("Mão 2:")
Card.print_pretty_cards(hand2)

print("\n=== Flop, Turn, River ===")
board = [deck.draw(1)[0] for _ in range(5)]
Card.print_pretty_cards(board)

print("\n=== Avaliação ===")
evaluator = Evaluator()

score1 = evaluator.evaluate(board, hand1)
score2 = evaluator.evaluate(board, hand2)

print(f"Score Hand 1: {score1} | {evaluator.class_to_string(evaluator.get_rank_class(score1))}")
print(f"Score Hand 2: {score2} | {evaluator.class_to_string(evaluator.get_rank_class(score2))}")

if score1 < score2:
    print("👉 Mão 1 venceu")
elif score2 < score1:
    print("👉 Mão 2 venceu")
else:
    print("🤝 Empate")
