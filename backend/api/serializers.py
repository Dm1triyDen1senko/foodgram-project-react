from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_extra_fields.fields import Base64ImageField

from recipes.models import (Ingredient, IngredientRecipe, Recipe, Selected,
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


class SelectedSerializer(serializers.ModelSerializer):
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
        model = Selected
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
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
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
    tags = TagSerializer(
        many=True,
        read_only=True
    )
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
        image = data.get('image')
        if not image:
            raise serializers.ValidationError(
                {'Добавьте изображение!'}
            )
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

    @transaction.atomic
    def create_ingredients(self, ingredients, recipe):
        IngredientRecipe.objects.bulk_create([
            IngredientRecipe(
                recipe=recipe,
                ingredient=Ingredient.objects.get(id=ingredient['id']),
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
