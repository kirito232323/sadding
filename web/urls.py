from django.contrib import admin
from django.urls import path, include
from webapp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("webapp.urls")),
    path('deletestock/<int:stock_id>/', views.deletestock, name='deletestock'),
]

