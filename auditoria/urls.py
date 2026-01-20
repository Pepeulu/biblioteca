from django.urls import path
from . import views

urlpatterns = [
    path('', views.auditoria, name='auditoria'),
    path('detalhes/<int:id>/', views.auditoria_detalhes, name='auditoria_detalhes'),
    path('limpar/', views.limpar_auditoria, name='limpar_auditoria'),
]