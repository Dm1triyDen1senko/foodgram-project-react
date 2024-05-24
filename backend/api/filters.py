from django.contrib.auth import get_user_model
from django_filters.rest_framework import FilterSet, filters
from rest_framework.filters import SearchFilter

from recipes import models

User = get_user_model()


class IngredientSearchFilter(SearchFilter):
    search_param = 'name'


class RecipeFilter(FilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=models.Tag.objects.all(),
    )
    is_favorited = filters.BooleanFilter(method='favorited')
    is_in_shopping_cart = filters.BooleanFilter(method='in_cart')

    class Meta:
        model = models.Recipe
        fields = ('tags', 'author')

    def favorited(self, queryset, name, value):
        if value is not None and self.request.user.is_authenticated:
            favorites = models.Favorites.objects.get(author=self.request.user)
            return queryset.filter(favorites=favorites)
        return queryset

    def in_cart(self, queryset, name, value):
        if value is not None and self.request.user.is_authenticated:
            shopping_list = models.ShoppingList.objects.get(
                author=self.request.user
            )
            return queryset.filter(shopping_cart_recipe=shopping_list)
        return queryset
