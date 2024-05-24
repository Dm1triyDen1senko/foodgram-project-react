from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from djoser.serializers import UserSerializer as DjoserUserSerializer

from .fields import Base64ImageField
from recipes.models import (Ingredient, IngredientRecipe, Recipe, Favorites,
                            ShoppingList, Tag)
from users.models import CustomUser, Follow


class UserSerializer(DjoserUserSerializer):

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
        )

    def get_is_subscribed(self, author):
        user = self.context.get('request').user

        return (
            user.is_authenticated
            and user.follower.filter(author=author).exists()
        )


class RecipeFollowSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FollowSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
        )

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user

        if user.is_authenticated:
            return Follow.objects.filter(user=user, author=obj).exists()
        return False

    def get_recipes(self, user):
        request = self.context.get('request')
        recipes_limit = request.GET.get('recipes_limit')
        recipes = Recipe.objects.filter(author=user)
        if recipes_limit:
            recipes = recipes[:int(recipes_limit)]
        serializer = RecipeFollowSerializer(recipes, many=True)
        return serializer.data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.id).count()


class FavoritesSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(
        source='recipe.name',
        read_only=True
    )
    image = serializers.ImageField(
        source='recipe.image',
        read_only=True
    )
    cooking_time = serializers.IntegerField(
        source='recipe.cooking_time',
        read_only=True
    )
    id = serializers.PrimaryKeyRelatedField(
        source='recipe',
        read_only=True
    )

    class Meta:
        model = Favorites
        fields = ('id', 'name', 'image', 'coocking_time')


class ShoppingListSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(
        source='recipe.name',
        read_only=True
    )
    image = serializers.ImageField(
        source='recipe.image',
        read_only=True
    )
    coocking_time = serializers.IntegerField(
        source='recipe.cooking_time',
        read_only=True
    )
    id = serializers.PrimaryKeyRelatedField(
        source='recipe',
        read_only=True
    )

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
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )
    name = serializers.ReadOnlyField(
        source='ingredient.name'
    )
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeListSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True)
    ingredients = IngredientRecipeSerializer(
        source='ingredientrecipes', many=True
    )
    is_favorited = serializers.BooleanField(read_only=True, default=False)
    is_in_shopping_cart = serializers.BooleanField(
        read_only=True,
        default=False
    )

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart',
                  'name', 'image', 'text', 'cooking_time')


class CreateUpdateRecipeSerializer(serializers.ModelSerializer):
    ingredients = IngredientRecipeSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'ingredients', 'tags', 'image', 'name', 'text', 'cooking_time',
        )
        extra_kwargs = {i: {'required': True} for i in fields}

    def validate(self, data):
        tags = data.get('tags')
        ingredients = data.get('ingredients')
        if not ingredients:
            raise ValidationError(
                dict(ingredients='Должен быть хотя бы 1 ингредиент!')
            )
        if not tags:
            raise ValidationError(dict(tags='Должен быть хотя бы 1 тег!'))
        if len(tags) != len(set(tags)):
            raise ValidationError('Дублирование в тэгах недопустимо!')
        ingredients_ids = [i['ingredient'].id for i in ingredients]
        if len(ingredients_ids) != len(set(ingredients_ids)):
            raise ValidationError('Ингредиенты не должны повторяться!')
        return super().validate(data)

    @transaction.atomic
    def create_ingredients(self, ingredients, recipe):
        IngredientRecipe.objects.bulk_create([
            IngredientRecipe(
                recipe=recipe,
                ingredient=ingredient['ingredient'],
                amount=ingredient['amount']
            ) for ingredient in ingredients])

    @transaction.atomic
    def create(self, validate_data):
        ingredients = validate_data.pop('ingredients')
        tags = validate_data.pop('tags')
        recipe = Recipe.objects.create(**validate_data)
        recipe.tags.set(tags)
        self.create_ingredients(ingredients, recipe)
        return recipe

    @transaction.atomic
    def update(self, recipe, validate_data):
        ingredients = validate_data.pop('ingredients')
        recipe.tags.clear()
        recipe.ingredients.clear()
        self.create_ingredients(recipe=recipe,
                                ingredients=ingredients)
        return super().update(recipe, validate_data)

    def to_representation(self, instance):
        return RecipeListSerializer(instance, context=self.context).data
