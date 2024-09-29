from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.generic import ListView, CreateView, UpdateView, \
    DetailView, DeleteView

from .forms import CommentForm
from .models import Post, Category, Comment

User = get_user_model()


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'

    def get_queryset(self):
        return (Post.objects
                .select_related('category', 'author', 'location')
                .filter(Q(is_published=True, category__is_published=True,
                          pub_date__lte=now()) | Q(author=self.request.user)))

    def get_context_data(self, **kwargs):
        context = super(PostDetailView, self).get_context_data(**kwargs)

        post = self.get_object()

        context['form'] = CommentForm()
        context['comments'] = (Comment.objects
                               .filter(post=post)
                               .select_related('author')
                               .order_by('created_at'))

        return context


class PostMixin:
    model = Post
    template_name = 'blog/create.html'


class PostFormMixin(PostMixin):
    fields = ('title', 'text', 'pub_date', 'location', 'category', 'image')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['pub_date'].widget = forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={'type': 'datetime-local'})

        return form


class PostEditMixin:
    pk_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user:
            return redirect('blog:post_detail',
                            post_id=self.kwargs['post_id'])

        return super().dispatch(request, *args, **kwargs)


class PostRedirectToProfileMixin:
    def get_success_url(self):
        return reverse('blog:profile',
                       kwargs={'username': self.request.user.username})


@method_decorator(login_required, name='dispatch')
class PostCreateView(PostFormMixin, PostRedirectToProfileMixin, CreateView):
    def form_valid(self, form):
        form.instance.author_id = self.request.user.id
        return super(PostCreateView, self).form_valid(form)


@method_decorator(login_required, name='dispatch')
class PostUpdateView(PostFormMixin, PostEditMixin,
                     UpdateView):
    pass


@method_decorator(login_required, name='dispatch')
class PostDeleteView(PostMixin, PostRedirectToProfileMixin,
                     PostEditMixin, DeleteView):
    pass


@login_required
def add_comment(request, post_id):
    if request.method == 'POST':
        form = CommentForm(request.POST)
        form.instance.author = request.user
        form.instance.post = get_object_or_404(Post, pk=post_id)
        if form.is_valid():
            form.save()

    return redirect('blog:post_detail', post_id=post_id)


class CommentEditMixin:
    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def get_success_url(self):
        return reverse_lazy('blog:post_detail',
                            kwargs={'post_id': self.kwargs['post_id']})

    def dispatch(self, request, *args, **kwargs):
        comment = self.get_object()
        post = get_object_or_404(Post, pk=self.kwargs['post_id'])
        if comment.post != post or comment.author != request.user:
            raise PermissionDenied("У вас недостаточно прав!")

        return super().dispatch(request, *args, **kwargs)


@method_decorator(login_required, name='dispatch')
class CommentUpdateView(CommentEditMixin, UpdateView):
    fields = ('text',)


@method_decorator(login_required, name='dispatch')
class CommentDeleteView(CommentEditMixin, DeleteView):
    pass


class PostListViewMixin:
    model = Post
    paginate_by = 10
    base_queryset = (Post.objects
                     .select_related('category', 'location', 'author')
                     .annotate(comment_count=Count('comment'))
                     .order_by('-pub_date'))


class PostListView(PostListViewMixin, ListView):
    template_name = 'blog/index.html'

    def get_queryset(self):
        return self.base_queryset.filter(is_published=True,
                                         category__is_published=True,
                                         pub_date__lte=now())


class CategoryPostListView(PostListViewMixin, ListView):
    template_name = 'blog/category.html'

    def get_queryset(self):
        category_slug = self.kwargs['category_slug']
        self.category = get_object_or_404(Category, slug=category_slug,
                                          is_published=True)
        return (self.base_queryset.filter(category=self.category,
                                          is_published=True,
                                          pub_date__lte=now()))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['category'] = self.category
        return context


class ProfilePostListView(PostListViewMixin, ListView):
    template_name = 'blog/profile.html'

    def get_queryset(self):
        username = self.kwargs['username']
        current_user = self.request.user
        self.profile_user = get_object_or_404(User, username=username)

        filters = {'author_id': self.profile_user.id}
        if current_user is None or current_user.id != self.profile_user.id:
            filters['is_published'] = True
            filters['pub_date__lte'] = now()

        return self.base_queryset.filter(**filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['profile'] = self.profile_user

        return context


@method_decorator(login_required, name='dispatch')
class ProfileUpdateView(UpdateView):
    model = User
    template_name = 'blog/user.html'
    fields = ('username', 'first_name', 'last_name', 'email')

    def get_object(self, queryset=None):
        return self.request.user
