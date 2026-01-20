from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from django.db.utils import IntegrityError
from datetime import date
import re


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


def extract_error_message(error_str):
    """Extrai mensagem de erro do MySQL"""
    match = re.search(r"'([^']*)'$", str(error_str))
    if match:
        return match.group(1)
    return str(error_str)


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
        ano = request.POST.get('ano') or None
        genero_id = request.POST.get('genero')
        editora_id = request.POST.get('editora')
        qtd = request.POST.get('quantidade')
        resumo = request.POST.get('resumo')

        try:
            execute("""
                INSERT INTO Livros 
                (Titulo, Autor_id, ISBN, Ano_publicacao, Genero_id, Editora_id, Quantidade_disponivel, Resumo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, [titulo, autor_id, isbn, ano, genero_id, editora_id, qtd, resumo])
            
            messages.success(request, f"Livro '{titulo}' cadastrado com sucesso!")
            return redirect('livros')
            
        except Exception as e:
            error_msg = extract_error_message(e)
            messages.error(request, f"Erro ao cadastrar livro: {error_msg}")
            
            # Retorna dados para preencher o formulário novamente
            autores = query("SELECT * FROM Autores")
            generos = query("SELECT * FROM Generos")
            editoras = query("SELECT * FROM Editoras")
            return render(request, 'livro_add.html', {
                'autores': autores,
                'generos': generos,
                'editoras': editoras,
                'titulo': titulo,
                'autor_id': autor_id,
                'isbn': isbn,
                'ano': ano,
                'genero_id': genero_id,
                'editora_id': editora_id,
                'qtd': qtd,
                'resumo': resumo
            })

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

        try:
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
            
            messages.success(request, f"Livro '{titulo}' atualizado com sucesso!")
            
            # Verificar se a quantidade mudou e informar
            livro_antigo = query("SELECT Quantidade_disponivel FROM Livros WHERE ID_livro = %s", [id])
            if livro_antigo and int(qtd) != livro_antigo[0]['Quantidade_disponivel']:
                messages.info(request, f"Estoque atualizado automaticamente pelo sistema")
            
            return redirect('livros')
            
        except Exception as e:
            error_msg = extract_error_message(e)
            messages.error(request, f"Erro ao atualizar livro: {error_msg}")

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
        livro = query("SELECT Titulo FROM Livros WHERE ID_livro = %s", [id])
        if livro:
            titulo = livro[0]['Titulo']
            execute("DELETE FROM Livros WHERE ID_livro = %s", [id])
            messages.success(request, f"Livro '{titulo}' excluído com sucesso!")
        else:
            messages.error(request, "Livro não encontrado")
    except IntegrityError:
        messages.error(request, "Não é possível excluir este livro pois existem empréstimos vinculados a ele")
    except Exception as e:
        error_msg = extract_error_message(e)
        messages.error(request, f"Erro ao excluir livro: {error_msg}")
    
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