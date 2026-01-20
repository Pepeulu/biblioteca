from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from django.db.utils import IntegrityError
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
def autores(request):
    dados = query("SELECT * FROM Autores")
    return render(request, 'autores.html', {'dados': dados})

@login_required
def autores_add(request):
    if request.method == 'POST':
        nac = request.POST.get('nacionalidade')
        bio = request.POST.get('bio')
        nome = request.POST.get('nome')
        data = request.POST.get('data_nasc') or None
        
        try:
            execute("INSERT INTO Autores (Nome_autor, Nacionalidade, Data_nascimento, Biografia) VALUES (%s, %s, %s, %s)",
                    [nome, nac, data, bio])
            messages.success(request, f"Autor '{nome}' cadastrado com sucesso!")
            return redirect('autores')
        except Exception as e:
            error_msg = extract_error_message(e)
            messages.error(request, f"Erro ao cadastrar autor: {error_msg}")
            return render(request, 'autor_add.html', {
                'nome': nome,
                'nacionalidade': nac,
                'data_nasc': data,
                'bio': bio
            })
    
    return render(request, 'autor_add.html')

@login_required
def autores_edit(request, id):
    if request.method == 'POST':
        nome = request.POST['nome']
        nac = request.POST['nacionalidade']
        data = request.POST['data_nasc']
        bio = request.POST['bio']
        
        try:
            execute("UPDATE Autores SET Nome_autor=%s, Nacionalidade=%s, Data_nascimento=%s, Biografia=%s WHERE ID_autor=%s",
                    [nome, nac, data, bio, id])
            messages.success(request, f"Autor '{nome}' atualizado com sucesso!")
            return redirect('autores')
        except Exception as e:
            error_msg = extract_error_message(e)
            messages.error(request, f"Erro ao atualizar autor: {error_msg}")
    
    autor = query("SELECT * FROM Autores WHERE ID_autor=%s", [id])[0]
    return render(request, 'autores_edit.html', {'autor': autor})

@login_required
def autores_delete(request, id):
    try:
        autor = query("SELECT Nome_autor FROM Autores WHERE ID_autor=%s", [id])
        if autor:
            nome = autor[0]['Nome_autor']
            execute("DELETE FROM Autores WHERE ID_autor=%s", [id])
            messages.success(request, f"Autor '{nome}' excluído com sucesso!")
        else:
            messages.error(request, "Autor não encontrado")
    except IntegrityError:
        messages.error(request, "Não é possível excluir este autor pois existem livros cadastrados vinculados a ele")
    except Exception as e:
        error_msg = extract_error_message(e)
        messages.error(request, f"Erro ao excluir autor: {error_msg}")
    
    return redirect('autores')

@login_required
def autor_detalhes(request, id):
    autor = query("SELECT * FROM Autores WHERE ID_autor=%s", [id])[0]
    return render(request, 'autor_detalhes.html', {'autor': autor})