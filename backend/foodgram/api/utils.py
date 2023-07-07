def get_shopping_cart(ingredients):
    shopping_list = 'Купить в магазине:'
    for ingredient in ingredients:
        shopping_list += (
            f"\n{ingredient['ingredient__name']} "
            f"({ingredient['ingredient__measurement_unit']}) - "
            f"{ingredient['amount']}")
    return shopping_list


def get_select_prefetch_related(queryset):
    return (
        queryset
        .select_related('author')
        .prefetch_related('tags', 'ingredients',
                          'recipe', 'shopping_cart',
                          'favorite_recipe')
    )
