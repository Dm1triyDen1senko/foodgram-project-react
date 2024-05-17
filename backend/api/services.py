import io

from django.http import HttpResponse
from django.db.models import Sum

from recipes.models import IngredientRecipe


def get_shopping_list(self, request, author) -> io.BytesIO:
    ingredients = IngredientRecipe.objects.filter(
        recipe__shopping_cart_recipe__author=author
    ).values(
        'ingredient__name', 'ingredient__measurement_unit'
    ).annotate(
        amounts=Sum('amount', distinct=True)).order_by('amounts')

    shopping_list = ''

    for ingredient in ingredients:
        shopping_list += (
            f'{ingredient["ingredient__name"]} - '
            f'{ingredient["amounts"]} '
            f'{ingredient["ingredient__measurement_unit"]}\n'
        )
    filename = 'shopping_list.txt'
    response = HttpResponse(shopping_list, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename={filename}'
    return response
