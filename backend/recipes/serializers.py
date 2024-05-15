import base64

from django.core.files.base import ContentFile
from recipes.models import (Ingredient, IngredientRecipe, Recipe, Selected,
                            ShoppingList, Tag)
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from users.serializers import CustomUserSerializer


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class SelectedSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(
        source='recipe.name',
        read_only=True)
    image = serializers.ImageField(
        source='recipe.image',
        read_only=True)
    coocking_time = serializers.IntegerField(
        source='recipe.cooking_time',
        read_only=True)
    id = serializers.PrimaryKeyRelatedField(
        source='recipe',
        read_only=True)

    class Meta:
        model = Selected
        fields = ('id', 'name', 'image', 'coocking_time')


class ShoppingListSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(
        source='recipe.name',
        read_only=True)
    image = serializers.ImageField(
        source='recipe.image',
        read_only=True)
    coocking_time = serializers.IntegerField(
        source='recipe.cooking_time',
        read_only=True)
    id = serializers.PrimaryKeyRelatedField(
        source='recipe',
        read_only=True)

    class Meta:
        model = ShoppingList
        fields = ('id', 'name', 'image', 'coocking_time')


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientRecipeSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    name = serializers.ReadOnlyField(
        source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeListSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)
    tags = TagSerializer(
        many=True,
        read_only=True)
    ingredients = IngredientRecipeSerializer(
        source='ingredientrecipes', many=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart',
                  'name', 'image', 'text', 'cooking_time')

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if not user.is_anonymous:
            return Selected.objects.filter(recipe=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if not user.is_anonymous:
            return ShoppingList.objects.filter(recipe=obj).exists()
        return False


class AddIngredientSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(allow_null=False)
    amount = serializers.IntegerField(
        allow_null=False,
        min_value=1,
        max_value=100000,
    )

    class Meta:
        model = Ingredient
        fields = ('id', 'amount')


class AddUpdateDeleteRecipeSerializer(serializers.ModelSerializer):
    ingredients = AddIngredientSerializer(
        many=True, allow_null=False, required=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        allow_null=False,
        allow_empty=False
    )
    image = Base64ImageField()
    author = serializers.HiddenField(
        default=serializers.CurrentUserDefault())

    class Meta:
        model = Recipe
        fields = ('ingredients', 'tags', 'image',
                  'name', 'text', 'cooking_time', 'author', 'id')

    def validate(self, data):
        ingredients = data.get('ingredients')
        tags = data.get('tags')
        cooking_time = data.get('cooking_time')
        if cooking_time == 0:
            raise serializers.ValidationError(
                {'Время приготовления не может быть меньше 1!'}
            )
        if ingredients is None or len(ingredients) <= 0:
            raise serializers.ValidationError(
                {'В рецепте нет ингридентов!'}
            )
        if tags is None or len(tags) <= 0:
            raise serializers.ValidationError(
                {'В рецепте нет тегов!'}
            )
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                {'Теги не должны повторяться!'}
            )
        if len(ingredients) != len(set([item['id'] for item in ingredients])):
            raise serializers.ValidationError(
                {'Ингредиенты не должны повторяться!'}
            )
        for ingredient in ingredients:
            if len(ingredient) > 0:
                is_ingredient = Ingredient.objects.filter(
                    pk=ingredient.get('id')
                )
                if not is_ingredient:
                    raise serializers.ValidationError(
                        {'Такого ингредиента не существует!'}
                    )
        return data

    def create_ingredients(self, ingredients, recipe):
        IngredientRecipe.objects.bulk_create([
            IngredientRecipe(
                recipe=recipe,
                ingredient=Ingredient.objects.get(id=ingredient['id']),
                amount=ingredient['amount']
            ) for ingredient in ingredients])

    def create(self, validate_data):
        ingredients = validate_data.pop('ingredients')
        tags = validate_data.pop('tags')
        recipe = Recipe.objects.create(**validate_data)
        recipe.tags.set(tags)
        self.create_ingredients(ingredients, recipe)
        return recipe

    def update(self, recipe, validate_data):
        ingredients = validate_data.pop('ingredients')
        tags = validate_data.pop('tags')
        if not ingredients or not tags:
            return ValidationError(
                {'В рецепте обязательно должен быть тег и ингредиент.'}
            )
        recipe = super().update(recipe, validate_data)
        recipe.tags.clear()
        recipe.ingredients.clear()
        recipe.tags.set(tags)
        self.create_ingredients(recipe=recipe,
                                ingredients=ingredients)
        recipe.save()
        return recipe

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}
        return RecipeListSerializer(instance, context=context).data
