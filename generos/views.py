from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
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
def generos(request):
    dados = query("SELECT * FROM Generos")
    return render(request, 'generos.html', {'dados': dados})

@login_required
def generos_add(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')

        try:
            execute(
                "INSERT INTO Generos (Nome_genero) VALUES (%s)",
                [nome]
            )
            return redirect('generos')

        except Exception as e:

            # mensagem original do MySQL trigger
            erro_mysql = e.args[1]

            messages.error(request, erro_mysql)

            return redirect('generos_add')

    return render(request, 'genero_add.html')

@login_required
def generos_edit(request, id):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        execute("UPDATE Generos SET Nome_genero=%s WHERE ID_genero=%s", [nome, id])
        return redirect('generos')
    genero = query("SELECT * FROM Generos WHERE ID_genero=%s", [id])[0]
    return render(request, 'generos_edit.html', {'genero': genero})

@login_required
def generos_delete(request, id):
    try:
        execute("DELETE FROM Generos WHERE ID_genero=%s", [id])
    except (TypeError, ValueError, IntegrityError):
        messages.error(request, "não foi possivel realizar")
    return redirect('generos')

@login_required
def genero_detalhes(request, id):
    genero = query("SELECT * FROM Generos WHERE ID_genero=%s", [id])[0]
    return render(request, 'genero_detalhes.html', {'genero': genero})