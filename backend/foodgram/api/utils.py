from django.http.response import FileResponse


def get_shopping_cart(ingredients):
    shopping_list = 'Купить в магазине:'
    for ingredient in ingredients:
        shopping_list += (
            f"\n{ingredient['ingredient__name']} "
            f"({ingredient['ingredient__measurement_unit']}) - "
            f"{ingredient['amount']}")
    return FileResponse(shopping_list, content_type='text/plain')
