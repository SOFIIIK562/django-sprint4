"""Render public publications using visibility-aware ORM queries."""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CommentForm, PostForm, ProfileForm
from .models import Category, Post

User = get_user_model()
POSTS_PER_PAGE = 10


def posts_with_details():
    """Fetch related data and comment counts for feeds."""
    return Post.objects.select_related(
        'category', 'location', 'author',
    ).annotate(comment_count=Count('comments')).order_by('-pub_date', '-pk')


def published_posts(queryset=None):
    """Return visible posts with the relations needed by templates."""
    if queryset is None:
        queryset = posts_with_details()
    return (
        queryset.filter(
            is_published=True, category__is_published=True,
            pub_date__lte=timezone.now(),
        )
    )


def page_context(request, queryset):
    """Paginate each feed using the same page size."""
    paginator = Paginator(queryset, POSTS_PER_PAGE)
    page = paginator.get_page(request.GET.get('page'))
    return {'page_obj': page, 'post_list': page.object_list}


def index(request):
    """Show a page of visible publications."""
    return render(request, 'blog/index.html',
                  page_context(request, published_posts()))


def post_detail(request, post_id):
    """Allow an author to preview their own hidden publication."""
    post = get_object_or_404(posts_with_details(), pk=post_id)
    if post.author != request.user:
        post = get_object_or_404(published_posts(), pk=post_id)
    return render(request, 'blog/detail.html', {
        'post': post, 'form': CommentForm(),
        'comments': post.comments.select_related('author').all(),
    })


def category_posts(request, category_slug):
    """Show visible publications in an existing published category."""
    category = get_object_or_404(
        Category, slug=category_slug, is_published=True,
    )
    post_list = published_posts().filter(category=category)
    context = page_context(request, post_list)
    context['category'] = category
    return render(request, 'blog/category.html', context)


def profile(request, username):
    """Show all posts to the owner and only public posts to others."""
    author = get_object_or_404(User, username=username)
    posts = posts_with_details().filter(author=author)
    if request.user != author:
        posts = published_posts(posts)
    context = page_context(request, posts)
    context['profile'] = author
    return render(request, 'blog/profile.html', context)


@login_required
def edit_profile(request):
    """Edit only the signed-in user's profile."""
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        author = form.save()
        return redirect('blog:profile', username=author.username)
    return render(request, 'blog/user.html', {'form': form})


@login_required
def create_post(request):
    """Assign a new post to the authenticated author."""
    form = PostForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, post_id):
    """Only the post author may change its contents."""
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post.pk)
    form = PostForm(request.POST or None, request.FILES or None, instance=post)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post.pk)
    return render(request, 'blog/create.html', {'form': form, 'post': post})


@login_required
def delete_post(request, post_id):
    """GET asks for confirmation; an author's POST performs deletion."""
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post.pk)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/create.html', {
        'post': post, 'form': PostForm(instance=post),
    })


@login_required
@require_POST
def add_comment(request, post_id):
    """Attach validated text to an accessible post."""
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        post = get_object_or_404(published_posts(), pk=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        return redirect('blog:post_detail', post_id=post.pk)
    return render(request, 'blog/detail.html', {
        'post': post, 'form': form,
        'comments': post.comments.select_related('author').all(),
    })


@login_required
def edit_comment(request, post_id, comment_id):
    """Validate both comment ownership and its parent publication."""
    post = get_object_or_404(Post, pk=post_id)
    comment = get_object_or_404(
        post.comments, pk=comment_id, author=request.user,
    )
    form = CommentForm(request.POST or None, instance=comment)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post.pk)
    return render(request, 'blog/comment.html', {
        'form': form, 'comment': comment, 'post': post,
    })


@login_required
def delete_comment(request, post_id, comment_id):
    """A confirmation page precedes an author's comment deletion."""
    post = get_object_or_404(Post, pk=post_id)
    comment = get_object_or_404(
        post.comments, pk=comment_id, author=request.user,
    )
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post.pk)
    return render(request, 'blog/comment.html', {
        'form': forms.Form(), 'comment': comment, 'post': post,
    })
