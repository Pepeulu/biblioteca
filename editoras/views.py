from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from datetime import date
from django.db.utils import IntegrityError

def login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_logado'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

def query(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def execute(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
    return True

@login_required
def editoras(request):
    dados = query("SELECT * FROM Editoras")
    return render(request, 'editoras.html', {'dados': dados})

@login_required
def editoras_add(request):
    if request.method == 'POST':
        nome = request.POST['nome']
        end = request.POST['endereco']
        execute("INSERT INTO Editoras (Nome_editora, Endereco_editora) VALUES (%s, %s)", [nome, end])
        return redirect('editoras')
    return render(request, 'editora_add.html')

@login_required
def editoras_edit(request, id):
    if request.method == 'POST':
        nome = request.POST['nome']
        end = request.POST['endereco']
        execute("UPDATE Editoras SET Nome_editora=%s, Endereco_editora=%s WHERE ID_editora=%s", [nome, end, id])
        return redirect('editoras')
    editora = query("SELECT * FROM Editoras WHERE ID_editora=%s", [id])[0]
    return render(request, 'editoras_edit.html', {'editora': editora})

@login_required
def editoras_delete(request, id):
    try:
        execute("DELETE FROM Editoras WHERE ID_editora=%s", [id])
    except (TypeError, ValueError, IntegrityError):
        messages.error(request, "não foi possivel realizar")
    return redirect('editoras')

@login_required
def editora_detalhes(request, id):
    editora = query("SELECT * FROM Editoras WHERE ID_editora=%s", [id])[0]
    return render(request, 'editora_detalhes.html', {'editora': editora})