from datetime import datetime

from django.shortcuts import render, get_object_or_404

from .models import Post, Category


def index(request):
    template = 'blog/index.html'
    posts = (Post.objects
             .select_related('category', 'location', 'author')
             .filter(is_published=True,
                     category__is_published=True,
                     pub_date__lte=datetime.now())
             .order_by('-pub_date')[:5])

    context = {"post_list": posts}
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'blog/detail.html'

    post = get_object_or_404(
        Post.objects.select_related('category', 'author', 'location'),
        pk=post_id,
        is_published=True,
        category__is_published=True,
        pub_date__lte=datetime.now())

    context = {"post": post}
    return render(request, template, context)


def category_posts(request, category_slug):
    template = 'blog/category.html'

    category = get_object_or_404(Category,
                                 slug=category_slug,
                                 is_published=True)

    posts = (Post.objects
             .select_related('category', 'location', 'author')
             .filter(category=category,
                     is_published=True,
                     pub_date__lte=datetime.now())
             .order_by('-pub_date'))

    context = {"category": category, "post_list": posts}
    return render(request, template, context)
