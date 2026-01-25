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
    Retorna exatamente a mensagem enviada pelo MySQL (SIGNAL)
    """
    try:
        return exception.args[1]
    except Exception:
        return str(exception)


@login_required
def editoras(request):
    dados = query("SELECT * FROM Editoras")
    return render(request, 'editoras.html', {'dados': dados})


@login_required
def editoras_add(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        end = request.POST.get('endereco')

        try:
            execute(
                "INSERT INTO Editoras (Nome_editora, Endereco_editora) VALUES (%s, %s)",
                [nome, end]
            )

            messages.success(request, f"Editora '{nome}' cadastrada com sucesso!")
            return redirect('editoras')

        except Exception as e:
            messages.error(request, get_mysql_message(e))

            return render(request, 'editora_add.html', {
                'nome': nome,
                'endereco': end
            })

    return render(request, 'editora_add.html')


@login_required
def editoras_edit(request, id):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        end = request.POST.get('endereco')

        try:
            execute(
                "UPDATE Editoras SET Nome_editora=%s, Endereco_editora=%s WHERE ID_editora=%s",
                [nome, end, id]
            )

            messages.success(request, f"Editora '{nome}' atualizada com sucesso!")
            return redirect('editoras')

        except Exception as e:
            messages.error(request, get_mysql_message(e))


    editora = query(
        "SELECT * FROM Editoras WHERE ID_editora=%s",
        [id]
    )[0]

    return render(request, 'editoras_edit.html', {'editora': editora})


@login_required
def editoras_delete(request, id):
    try:
        editora = query(
            "SELECT Nome_editora FROM Editoras WHERE ID_editora=%s",
            [id]
        )

        if not editora:
            messages.error(request, "Editora não encontrada")
            return redirect('editoras')

        nome = editora[0]['Nome_editora']

        execute(
            "DELETE FROM Editoras WHERE ID_editora=%s",
            [id]
        )

        messages.success(request, f"Editora '{nome}' excluída com sucesso!")

    except IntegrityError:
        messages.error(
            request,
            "Não é possível excluir esta editora pois existem livros vinculados a ela"
        )

    except Exception as e:
        messages.error(request, get_mysql_message(e))

    return redirect('editoras')


@login_required
def editora_detalhes(request, id):
    editora = query(
        "SELECT * FROM Editoras WHERE ID_editora=%s",
        [id]
    )[0]

    return render(request, 'editora_detalhes.html', {'editora': editora})
