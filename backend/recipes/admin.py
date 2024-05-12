from django.contrib import admin

from .models import Tag, Recipe, Ingredient, ShoppingList, Selected


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'slug')


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'author', 'image', 'text',
        'cooking_time', 'count_in_favorite'
    )
    list_filter = ('tags', 'author', 'name')
    readonly_fields = ('count_in_favorite',)

    @admin.display(description='Счетчик избранного')
    def count_in_favorite(self, recipe):
        return recipe.favoriterecipes.count()


@admin.register(ShoppingList)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('author', 'recipe')
    list_filter = list_display


@admin.register(Selected)
class FavoriteRecipeAdmin(admin.ModelAdmin):
    list_display = ('author', 'recipe')
    list_filter = list_display
