from django.shortcuts import render, redirect
from django.db import connection, transaction
from django.contrib import messages
from django.db.utils import IntegrityError, DatabaseError


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
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(sql, params or [])


def get_mysql_message(exception):
    """
    Retorna exatamente a mensagem enviada pelo MySQL/Trigger
    """
    try:
        return exception.args[1]
    except Exception:
        return str(exception)


@login_required
def autores(request):
    dados = query("SELECT * FROM Autores")
    return render(request, 'autores.html', {'dados': dados})


@login_required
def autores_add(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        nac = request.POST.get('nacionalidade')
        bio = request.POST.get('bio')
        data = request.POST.get('data_nasc') or None

        try:
            execute("""
                INSERT INTO Autores 
                (Nome_autor, Nacionalidade, Data_nascimento, Biografia) 
                VALUES (%s, %s, %s, %s)
            """, [nome, nac, data, bio])

            messages.success(request, f"Autor '{nome}' cadastrado com sucesso!")
            return redirect('autores')

        except Exception as e:
            messages.error(request, get_mysql_message(e))

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
        nome = request.POST.get('nome')
        nac = request.POST.get('nacionalidade')
        data = request.POST.get('data_nasc')
        bio = request.POST.get('bio')

        try:
            execute("""
                UPDATE Autores 
                SET Nome_autor=%s,
                    Nacionalidade=%s,
                    Data_nascimento=%s,
                    Biografia=%s
                WHERE ID_autor=%s
            """, [nome, nac, data, bio, id])

            messages.success(request, f"Autor '{nome}' atualizado com sucesso!")
            return redirect('autores')

        except Exception as e:
            messages.error(request, get_mysql_message(e))


    autor = query(
        "SELECT * FROM Autores WHERE ID_autor=%s",
        [id]
    )[0]

    return render(request, 'autores_edit.html', {'autor': autor})


@login_required
def autores_delete(request, id):
    try:
        autor = query(
            "SELECT Nome_autor FROM Autores WHERE ID_autor=%s",
            [id]
        )

        if not autor:
            messages.error(request, "Autor não encontrado")
            return redirect('autores')

        nome = autor[0]['Nome_autor']

        execute(
            "DELETE FROM Autores WHERE ID_autor=%s",
            [id]
        )

        messages.success(request, f"Autor '{nome}' excluído com sucesso!")

    except IntegrityError:
        messages.error(
            request,
            "Não é possível excluir este autor pois existem livros vinculados a ele"
        )

    except Exception as e:
        messages.error(request, get_mysql_message(e))

    return redirect('autores')

@login_required
def autor_detalhes(request, id):
    autor = query("SELECT * FROM Autores WHERE ID_autor=%s", [id])[0]
    return render(request, 'autor_detalhes.html', {'autor': autor})