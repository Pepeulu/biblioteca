from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from django.db.utils import IntegrityError
from datetime import date


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
def livros(request):
    dados = query("SELECT * FROM Livros")
    return render(request, 'livros.html', {'dados': dados})


@login_required
def livros_add(request):
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        autor_id = request.POST.get('autor')
        isbn = request.POST.get('isbn')
        ano = request.POST.get('ano') or str(date.today())
        genero_id = request.POST.get('genero')
        editora_id = request.POST.get('editora')
        qtd = request.POST.get('quantidade')
        resumo = request.POST.get('resumo')

        if not autor_id:
            messages.error(request, "Você deve selecionar um autor para o livro.")
            return redirect('livros_add')
        if not genero_id:
            messages.error(request, "Você deve selecionar um genero literário para o livro.")
            return redirect('livros_add')
        if not editora_id:
            messages.error(request, "Você deve selecionar uma editora para o livro.")
            return redirect('livros_add')
        if not titulo:
            messages.error(request, "Você deve indicar um titulo para o livro.")
            return redirect('livros_add')
        if not isbn:
            messages.error(request, "Você deve indicar um isbn para o livro.")
            return redirect('livros_add')
        if not qtd:
            messages.error(request, "Você deve indicar uma quantidade para o livro.")
            return redirect('livros_add')
        elif int(qtd) < 0:
            messages.error(request, "Você deve indicar uma quantidade valida para o livro.")
            return redirect('livros_add')
        if not resumo:
            messages.error(request, "Você deve indicar um resumo para o livro.")
            return redirect('livros_add')
        

        execute("""
            INSERT INTO Livros 
            (Titulo, Autor_id, ISBN, Ano_publicacao, Genero_id, Editora_id, Quantidade_disponivel, Resumo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, [titulo, autor_id, isbn, ano, genero_id, editora_id, qtd, resumo])

        return redirect('livros')

    autores = query("SELECT * FROM Autores")
    generos = query("SELECT * FROM Generos")
    editoras = query("SELECT * FROM Editoras")
    return render(request, 'livro_add.html', {
        'autores': autores,
        'generos': generos,
        'editoras': editoras
    })


@login_required
def livros_edit(request, id):
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        autor_id = request.POST.get('autor')
        isbn = request.POST.get('isbn')
        ano = request.POST.get('ano')
        genero_id = request.POST.get('genero')
        editora_id = request.POST.get('editora')
        qtd = request.POST.get('quantidade')
        resumo = request.POST.get('resumo')

        execute("""
            UPDATE Livros 
            SET Titulo = %s, 
                Autor_id = %s, 
                ISBN = %s, 
                Ano_publicacao = %s,
                Genero_id = %s, 
                Editora_id = %s, 
                Quantidade_disponivel = %s, 
                Resumo = %s
            WHERE ID_livro = %s
        """, [titulo, autor_id, isbn, ano, genero_id, editora_id, qtd, resumo, id])

        return redirect('livros')

    livro = query("SELECT * FROM Livros WHERE ID_livro = %s", [id])[0]
    autores = query("SELECT * FROM Autores")
    generos = query("SELECT * FROM Generos")
    editoras = query("SELECT * FROM Editoras")
    return render(request, 'livros_edit.html', {
        'livro': livro,
        'autores': autores,
        'generos': generos,
        'editoras': editoras
    })


@login_required
def livros_delete(request, id):
    try:
        execute("DELETE FROM Livros WHERE ID_livro = %s", [id])
    except (TypeError, ValueError, IntegrityError):
        messages.error(request, "não foi possivel realizar")
    return redirect('livros')


@login_required
def livro_detalhes(request, id):
    livro = query("""
        SELECT Livros.*, 
               Autores.Nome_autor, 
               Generos.Nome_genero, 
               Editoras.Nome_editora
        FROM Livros
        LEFT JOIN Autores ON Livros.Autor_id = Autores.ID_autor
        LEFT JOIN Generos ON Livros.Genero_id = Generos.ID_genero
        LEFT JOIN Editoras ON Livros.Editora_id = Editoras.ID_editora
        WHERE Livros.ID_livro = %s
    """, [id])[0]

    return render(request, 'livro_detalhes.html', {'livro': livro})
