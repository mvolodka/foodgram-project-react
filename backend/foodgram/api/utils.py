from django.http.response import FileResponse


def get_shopping_cart(ingredients):
    shopping_list = 'Купить в магазине:'
    for ingredient in ingredients:
        shopping_list += (
            f"\n{ingredient['ingredient__name']} "
            f"({ingredient['ingredient__measurement_unit']}) - "
            f"{ingredient['amount']}")
    file = 'shopping_list.txt'
    response = FileResponse(shopping_list, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{file}.txt"'
    return response
