from users.models import CustomUser, Follow
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny, SAFE_METHODS
from rest_framework.response import Response
from .permissions import IsOwnerOrAdminOrReadOnly
from users.serializers import FollowSerializer, RecipeFollowSerializer
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from recipes.models import (
    Ingredient, Tag, Recipe, ShoppingList, Selected
)
from django.db.models import Sum
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from api.filters import RecipeFilter
from recipes.models import (Selected, Ingredient, Recipe,
                            ShoppingList, IngredientRecipe)
from api.permissions import IsOwnerOrAdminOrReadOnly
from recipes.serializers import (
    AddUpdateDeleteRecipeSerializer,
    IngredientSerializer,
    TagSerializer,
    RecipeListSerializer
)
from djoser.views import UserViewSet
from .import paginations


class CustomUserViewSet(UserViewSet):
    permission_classes = (AllowAny,)
    pagination_class = paginations.LimitPageNumberPagination

    def get_permissions(self):
        if self.request.path.endswith('me/'):
            return (IsAuthenticated(),)
        elif self.action in ('retrieve', 'list'):
            return (AllowAny(),)
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'subscribe':
            return FollowSerializer
        return super().get_serializer_class()

    @action(
        detail=True, methods=('POST', 'DELETE'),
        pagination_class=None,
    )
    def subscribe(self, request, id):
        if not CustomUser.objects.filter(pk=id).exists():
            return Response(
                dict(error='Такого пользователя не существует!'),
                status=status.HTTP_404_NOT_FOUND
            )
        author = CustomUser.objects.get(pk=id)
        user = request.user

        if not user.is_authenticated:
            return Response(
                status=status.HTTP_401_UNAUTHORIZED
            )

        if request.method == 'POST':
            if user == author:
                return Response(
                    dict(error='Невозможно подписываться на самого себя!'),
                    status=status.HTTP_400_BAD_REQUEST
                )
            if Follow.objects.filter(
                user=user, author=author
            ).exists():
                return Response(
                    dict(error='Вы уже подписаны на этого пользователя!'),
                    status=status.HTTP_400_BAD_REQUEST
                )
            Follow.objects.create(user=user, author=author)
            serializer = FollowSerializer(
                author, context=dict(request=request)
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            connection = Follow.objects.filter(user=user, author=author)
            if connection.exists():
                connection.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                dict(error='Вы больше не подписаны на этого пользователя!'),
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=False, methods=('GET',),
        pagination_class=paginations.LimitPageNumberPagination,
    )
    def subscriptions(self, request):
        queryset = CustomUser.objects.filter(author__user=self.request.user)
        serializer = FollowSerializer(
            self.paginate_queryset(queryset),
            context=dict(request=request),
            many=True,
        )
        return self.get_paginated_response(serializer.data)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny, )
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny, )
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_fields = ('name',)
    search_fields = ('name',)
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = (IsOwnerOrAdminOrReadOnly,)
    filterset_class = RecipeFilter
    filter_backends = (DjangoFilterBackend,)
    pagination_class = paginations.LimitPageNumberPagination
    http_method_names = ['get', 'post', 'delete', 'patch']

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeListSerializer
        return AddUpdateDeleteRecipeSerializer

    # def perform_create(self, serializer):
    #     serializer.save(author=self.request.user)

    # def partial_update(self, request, *args, **kwargs):
    #     recipe = get_object_or_404(Recipe, id=self.kwargs['pk'])
    #     if self.request.user == recipe.author:
    #         return super().partial_update(request)
    #     else:
    #         return Response(
    #             status=status.HTTP_403_FORBIDDEN
    #         )

    # def destroy(self, request, *args, **kwargs):
    #     recipe = get_object_or_404(Recipe, id=self.kwargs['pk'])
    #     if self.request.user == recipe.author:
    #         return super().destroy(request)
    #     else:
    #         return Response(
    #             status=status.HTTP_403_FORBIDDEN
    #         )

    def create_connection(self, model, user, pk):
        if not Recipe.objects.filter(id=pk).exists():
            return Response(
                dict(errors='Рецепт не существует'),
                status=status.HTTP_400_BAD_REQUEST
            )
        if model.objects.filter(author=user, recipe__id=pk).exists():
            return Response(
                dict(errors='Рецепт уже в списке'),
                status=status.HTTP_400_BAD_REQUEST
            )
        recipe = Recipe.objects.get(pk=pk)
        model.objects.create(author=user, recipe=recipe)
        serializer = RecipeFollowSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete_connection(self, model, user, pk):
        if not Recipe.objects.filter(id=pk).exists():
            return Response(
                dict(errors='Рецепт не существует'),
                status=status.HTTP_404_NOT_FOUND
            )
        connection = model.objects.filter(author=user, recipe__id=pk)
        if connection.exists():
            connection.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            dict(errors='Рецепт был удален ранее'),
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=('POST', 'DELETE'),)
    def favorite(self, request, pk=None):
        if request.method == 'POST':
            return self.create_connection(
                Selected, request.user, pk
            )
        return self.delete_connection(
            Selected, request.user, pk
        )

    @action(detail=True, methods=('POST', 'DELETE'),)
    def shopping_cart(self, request, pk=None):
        if request.method == 'POST':
            return self.create_connection(
                ShoppingList, request.user, pk
            )
        return self.delete_connection(
            ShoppingList, request.user, pk
        )

    # @action(
    #     detail=False,
    #     methods=('get',),
    #     pagination_class=None,
    #     url_path='download_shopping_cart',
    #     permission_classes=(IsAuthenticated,)
    # )
    # def download_file(self, request):
    #     user = request.user
    #     if not ShoppingList.objects.filter(user_id=user.id).exists():
    #         return Response(
    #             'Корзина пуста!', status=status.HTTP_400_BAD_REQUEST)
    #     ingredients = IngredientRecipe.objects.filter(
    #         recipe__shopping_cart_recipe__user=user
    #     ).values(
    #         'ingredient__name',
    #         'ingredient__measurement_unit'
    #     ).annotate(amount=Sum('amount'))
    #     shopping_list = (
    #         f'Список покупок для: {user.get_full_name()}\n\n'
    #     )
    #     shopping_list += '\n'.join([
    #         f' - {ingredient["ingredient__name"]} '
    #         f' {ingredient["ingredient__measurement_unit"]}'
    #         f' - {ingredient["amount"]}'
    #         for ingredient in ingredients
    #     ])
    #     shopping_list += '\n\nFoodgram'
    #     filename = f'{user.username}_shopping_cart.txt'
    #     response = HttpResponse(shopping_list, content_type='text/plain')
    #     response['Content-Disposition'] = f'attachment; filename={filename}'
    #     return response

    @action(detail=False,
            methods=('get',),
            pagination_class=None,
            url_path='download_shopping_cart',
            permission_classes=(IsAuthenticated,),)
    def download_file(self, request):
        user = request.user
        if not ShoppingList.objects.filter(author_id=user.id).exists():
            return Response(
                'В корзине нет товаров.', status=status.HTTP_400_BAD_REQUEST)
        ingredients = IngredientRecipe.objects.filter(
            recipe__shopping_cart_recipe__author=user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(amount=Sum('amount'))
        shopping_list = (
            f'Список покупок для: {user.get_full_name()}\n\n'
        )
        shopping_list += '\n'.join([
            f' - {ingredient["ingredient__name"]} '
            f' {ingredient["ingredient__measurement_unit"]}'
            f' - {ingredient["amount"]}'
            for ingredient in ingredients
        ])
        shopping_list += '\n\nFoodgram'
        filename = f'{user.username}_shopping_cart.txt'
        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response
