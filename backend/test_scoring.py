
def calculate_score(questions_data):
    total_weighted_score = 0.0
    max_weighted_possible = 0.0
    
    print(f"{'Score':<10} | {'Diff':<10} | {'Weight':<10} | {'Weighted Score':<15}")
    print("-" * 55)
    
    for q in questions_data:
        score = q['score']
        difficulty = q['difficulty']
        weight = 1.0 + (difficulty - 1) * 0.5
        
        weighted_val = score * weight
        total_weighted_score += weighted_val
        max_weighted_possible += 100.0 * weight
        
        print(f"{score:<10} | {difficulty:<10} | {weight:<10} | {weighted_val:<15}")
    
    percentage = (total_weighted_score / max_weighted_possible * 100) if max_weighted_possible > 0 else 0
    final_rounded = round(percentage)
    
    simple_avg = sum(q['score'] for q in questions_data) / len(questions_data)
    
    print("-" * 55)
    print(f"Total Weighted: {total_weighted_score}")
    print(f"Max Weighted:   {max_weighted_possible}")
    print(f"Final %:        {percentage:.2f}%")
    print(f"Rounded Result: {final_rounded}")
    print(f"Simple Average: {simple_avg:.2f}%")
    return final_rounded

print("--- ТЕСТ 1: Твой случай (73/1 и 71/2) ---")
calculate_score([
    {'score': 73, 'difficulty': 1},
    {'score': 71, 'difficulty': 2}
])

print("\n--- ТЕСТ 2: Контрастный случай (100/1 и 0/5) ---")
# Ожидаем сильный перекос в сторону 0, так как вес сложности 5 в 3 раза выше
calculate_score([
    {'score': 100, 'difficulty': 1},
    {'score': 0, 'difficulty': 5}
])

print("\n--- ТЕСТ 3: Контрастный случай (0/1 и 100/5) ---")
# Ожидаем высокий балл, так как сложный вопрос решен верно
calculate_score([
    {'score': 0, 'difficulty': 1},
    {'score': 100, 'difficulty': 5}
])
