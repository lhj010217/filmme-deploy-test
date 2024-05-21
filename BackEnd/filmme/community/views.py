from rest_framework import viewsets, mixins, filters, status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from django.utils import timezone

from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.contrib.auth import get_user_model

from .models import Community, CommunityComment, CommunityLike
from .serializers import *
from .paginations import CommunityCommentPagination, CommunityPagination
from .permissions import IsOwnerOrReadOnly

# Create your views here.
#리스트 생성
class CommunityListCreate(generics.ListCreateAPIView):
    queryset = Community.objects.all()
    serializer_class = CommunityCreateUpdateSerializer
# 정렬 기능
class CommunityOrderingFilter(filters.OrderingFilter):
    def filter_queryset(self, request, queryset, view):
        order_by = request.query_params.get(self.ordering_param)
        if order_by == 'popular':
            return queryset.order_by('-view_cnt') # 조회순
        elif order_by == 'like':
            return queryset.order_by('-likes_cnt') # 좋아요순
        else:
            # 기본은 최신순으로 설정
            return queryset.order_by('-created_at')
# 커뮤니티 목록
class CommunityViewSet(viewsets.GenericViewSet,
                    mixins.ListModelMixin
                ):
    filter_backends = [CommunityOrderingFilter, SearchFilter]
    search_fields = ['ai__title'] 
    pagination_class = CommunityPagination

    def get_serializer_class(self):
            queryset = self.get_queryset()
            category = queryset.values_list('category', flat=True).first()
            if category == 'cinema_tip':
                return TipListSerializer
            if category == 'common':
                return CommonListSerializer
            else:
                return suggestionListSerializer
            
    def retrieve(self):
        instance = self.get_object()
        instance.view_cnt += 1
        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def get_permissions(self):
        if self.action == "list":
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(writer = self.request.user)

    def get_queryset(self):
        category = self.kwargs.get('category')

        User = get_user_model()
        user = self.request.user if isinstance(self.request.user, User) else None

        queryset = Community.objects.filter(category=category).annotate(
            likes_cnt=Count('likes_community', distinct=True)
        )
        return queryset
        
# 게시물 작성 & 수정
class CommunityPostViewSet(viewsets.GenericViewSet,
                            mixins.CreateModelMixin,
                            mixins.UpdateModelMixin,
                            mixins.DestroyModelMixin
                            ):
    serializer_class = CommunityCreateUpdateSerializer

    queryset = Community.objects.all()

    def get_permissions(self):
        if self.action in ['create']:
            return [IsAuthenticated()]
        else:
            return [IsOwnerOrReadOnly()]
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data
        
        if 'title' in data or 'content' in data:
            instance.title = data.get('title', instance.title)
            instance.content = data.get('content', instance.content)
            instance.updated_at = timezone.now()
            instance.save()
            
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.view_cnt += 1
        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
# 커뮤니티 디테일
class CommunityDetailViewSet(viewsets.GenericViewSet,
                            mixins.RetrieveModelMixin,
                            ):
    def get_serializer_class(self):
            queryset = self.get_queryset()
            category = queryset.values_list('category', flat=True).first()
            if category == 'common':
                return CommonDetailSerializer
            if category == 'cinema_tip':
                return cinema_tipDetailSerializer
            else:
                return suggestionDetailSerializer
    
    def get_permissions(self):
        if self.action in ['like_action']:
            return [IsAuthenticated()]
        elif self.action in ['retrieve']:
            return [AllowAny()]
        else:
            return []
    
    def get_queryset(self):
        category = self.kwargs.get('category')

        User = get_user_model()
        user = self.request.user if isinstance(self.request.user, User) else None

        queryset = Community.objects.filter(category=category).annotate(
            likes_cnt=Count('likes_community', distinct=True)
        )
        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.view_cnt += 1 
        instance.save()  

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(methods=['POST', 'DELETE'], detail=True, url_path='like')
    def like_action(self, request, *args, **kwargs):
        community = self.get_object()
        user = request.user
        community_like, created = CommunityLike.objects.get_or_create(community=community, user=user)

        if request.method == 'POST':
            community_like.save()
            return Response({"detail": "좋아요를 눌렀습니다."})
        
        elif request.method == 'DELETE':
            community_like.delete()
            return Response({"detail": "좋아요를 취소하였습니다."})
