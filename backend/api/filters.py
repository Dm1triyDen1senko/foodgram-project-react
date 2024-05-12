# from django_filters.rest_framework import FilterSet, filters
# from rest_framework.filters import SearchFilter

# from recipes.models import Recipe, CustomUser, Tag


# class IngredientSearchFilter(SearchFilter):
#     search_param = 'name'


# class RecipeFilter(FilterSet):
#     author = filters.ModelChoiceFilter(
#         queryset=CustomUser.objects.all())
#     tags = filters.ModelMultipleChoiceFilter(
#         field_name='tags__slug',
#         to_field_name='slug',
#         queryset=Tag.objects.all(),
#     )
#     is_in_shopping_cart = filters.NumberFilter(
#         method='filter_is_in_shopping_cart')
#     is_favorited = filters.NumberFilter(
#         method='filter_is_favorited')

#     class Meta:
#         model = Recipe
#         fields = ('tags', 'author', 'is_favorited', 'is_in_shopping_cart')

#     def filter_is_favorited(self, queryset, name, value):
#         if self.request.user.is_authenticated and value:
#             return queryset.filter(favorite__author=self.request.user)
#         return queryset

#     def filter_is_in_shopping_cart(self, queryset, name, value):
#         if self.request.user.is_authenticated and value:
#             return queryset.filter(shopping_cart__author=self.request.user)
#         return queryset


from django.contrib.auth import get_user_model
from recipes.models import ShoppingList, Selected
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

    # def favorited(self, queryset, name, value):
    #     if value and not self.request.user.is_anonymous:
    #         return queryset.filter(favoriterecipes__user=self.request.user)
    #     return queryset

    def favorited(self, queryset, name, value):
        if value and not self.request.user.is_anonymous:
            selected = Selected.objects.get(author=self.request.user)
            return queryset.filter(selected=selected)
        return queryset

    # def in_cart(self, queryset, name, value):
    #     if value and not self.request.user.is_anonymous:
    #         return queryset.filter(shoppinglist__user=self.request.user)
    #     return queryset

    def in_cart(self, queryset, name, value):
        if value and not self.request.user.is_anonymous:
            shopping_list = ShoppingList.objects.get(author=self.request.user)
            return queryset.filter(shoppinglist=shopping_list)
        return queryset
