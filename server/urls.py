from django.contrib import admin
from django.urls import path

from server.drafts import views
from server.drafts.rpc import rpc

urlpatterns = [
    path("admin/", admin.site.urls),
    rpc.urls,
    path("draft/<int:draft_id>/", views.draft_page),
    path("subreddits/", views.subreddits_page),
    path("", views.queue_page),
]
