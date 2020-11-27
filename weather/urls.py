from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="index"),

    path("<str:add>", views.chgaddress, name="chgaddress"),

    path('<str:add>/naver/', views.naver, name="naver"),

]