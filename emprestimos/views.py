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
def emprestimos(request):
    usuario_id = request.session.get('usuario_logado')

    dados = query("""
        SELECT Emprestimos.ID_emprestimo,
               Usuarios.Nome_usuario,
               Livros.Titulo,
               Emprestimos.Data_emprestimo,
               Emprestimos.Data_devolucao_prevista,
               Emprestimos.Data_devolucao_real,
               Emprestimos.Status_emprestimo
        FROM Emprestimos
        JOIN Usuarios ON Emprestimos.Usuario_id = Usuarios.ID_usuario
        JOIN Livros ON Emprestimos.Livro_id = Livros.ID_livro
        WHERE Usuarios.ID_usuario = %s
        ORDER BY Emprestimos.ID_emprestimo DESC
    """, [usuario_id])

    return render(request, 'emprestimos.html', {'dados': dados})


@login_required
def emprestimos_add(request):
    usuario_id = request.session.get('usuario_logado')

    if request.method == 'POST':
        livro = request.POST.get('livro')
        data_emp = request.POST.get('data_emp') or None
        data_prev = request.POST.get('data_prev') or None
        status = 'pendente'

        try:
            execute("""
                INSERT INTO Emprestimos
                (Usuario_id, Livro_id, Data_emprestimo, Data_devolucao_prevista, Status_emprestimo)
                VALUES (%s, %s, %s, %s, %s)
            """, [usuario_id, livro, data_emp, data_prev, status])

            livro_info = query(
                "SELECT Titulo FROM Livros WHERE ID_livro = %s",
                [livro]
            )

            titulo_livro = livro_info[0]['Titulo'] if livro_info else "Livro"

            messages.success(
                request,
                f"Empréstimo do livro '{titulo_livro}' registrado com sucesso!"
            )

            messages.info(
                request,
                "O estoque do livro foi atualizado automaticamente"
            )

            emp_criado = query("""
                SELECT Data_emprestimo, Data_devolucao_prevista
                FROM Emprestimos
                WHERE Usuario_id = %s AND Livro_id = %s
                ORDER BY ID_emprestimo DESC
                LIMIT 1
            """, [usuario_id, livro])

            if emp_criado:
                if not data_emp:
                    messages.info(
                        request,
                        f"Data de empréstimo definida automaticamente: {emp_criado[0]['Data_emprestimo']}"
                    )

                if not data_prev:
                    messages.info(
                        request,
                        f"Data de devolução prevista definida automaticamente: {emp_criado[0]['Data_devolucao_prevista']} (14 dias)"
                    )

            return redirect('emprestimos')

        except Exception as e:
            messages.error(request, get_mysql_message(e))


    livros = query(
        "SELECT * FROM Livros WHERE Quantidade_disponivel > 0"
    )

    return render(request, 'emprestimo_add.html', {'livros': livros})


@login_required
def emprestimos_edit(request, id):
    if request.method == 'POST':
        usuario = request.POST.get('usuario')
        novo_livro = request.POST.get('livro')
        data_emp = request.POST.get('data_emp')
        data_prev = request.POST.get('data_prev')
        data_real = request.POST.get('data_real') or None
        novo_status = request.POST.get('status')

        try:
            emprestimo_atual = query(
                "SELECT Status_emprestimo FROM Emprestimos WHERE ID_emprestimo = %s",
                [id]
            )

            status_antigo = emprestimo_atual[0]['Status_emprestimo'] if emprestimo_atual else None

            execute("""
                UPDATE Emprestimos
                SET Usuario_id = %s,
                    Livro_id = %s,
                    Data_emprestimo = %s,
                    Data_devolucao_prevista = %s,
                    Data_devolucao_real = %s,
                    Status_emprestimo = %s
                WHERE ID_emprestimo = %s
            """, [usuario, novo_livro, data_emp, data_prev, data_real, novo_status, id])

            messages.success(request, "Empréstimo atualizado com sucesso!")

            if status_antigo != 'devolvido' and novo_status.lower() == 'devolvido':
                messages.info(request, "O estoque do livro foi incrementado automaticamente")

                emp_info = query("""
                    SELECT DATEDIFF(
                        COALESCE(Data_devolucao_real, CURDATE()),
                        Data_devolucao_prevista
                    ) AS atraso
                    FROM Emprestimos
                    WHERE ID_emprestimo = %s
                """, [id])

                if emp_info and emp_info[0]['atraso'] > 0:
                    dias_atraso = emp_info[0]['atraso']
                    multa = dias_atraso * 2.00

                    messages.warning(
                        request,
                        f"Multa de R$ {multa:.2f} aplicada automaticamente ({dias_atraso} dias de atraso)"
                    )

            if not data_real and novo_status.lower() == 'devolvido':
                messages.info(
                    request,
                    "Data de devolução real foi definida automaticamente para hoje"
                )

            return redirect('emprestimos')

        except Exception as e:
            messages.error(request, get_mysql_message(e))


    emprestimo = query(
        "SELECT * FROM Emprestimos WHERE ID_emprestimo = %s",
        [id]
    )[0]

    usuarios = query("SELECT * FROM Usuarios")
    livros = query("SELECT * FROM Livros")

    return render(request, 'emprestimos_edit.html', {
        'emprestimo': emprestimo,
        'usuarios': usuarios,
        'livros': livros
    })


@login_required
def emprestimos_delete(request, id):
    try:
        emp_info = query("""
            SELECT e.Status_emprestimo, l.Titulo
            FROM Emprestimos e
            JOIN Livros l ON e.Livro_id = l.ID_livro
            WHERE e.ID_emprestimo = %s
        """, [id])

        if not emp_info:
            messages.error(request, "Empréstimo não encontrado")
            return redirect('emprestimos')

        status = emp_info[0]['Status_emprestimo']
        titulo = emp_info[0]['Titulo']

        execute(
            "DELETE FROM Emprestimos WHERE ID_emprestimo = %s",
            [id]
        )

        messages.success(request, "Empréstimo excluído com sucesso!")

        if status.lower() != 'devolvido':
            messages.info(
                request,
                f"O livro '{titulo}' foi devolvido automaticamente ao estoque"
            )

    except IntegrityError:
        messages.error(request, "Não é possível excluir este empréstimo")

    except Exception as e:
        messages.error(request, get_mysql_message(e))

    return redirect('emprestimos')


@login_required
def emprestimo_detalhes(request, id):
    emprestimo = query("""
        SELECT Emprestimos.*,
               Usuarios.Nome_usuario,
               Livros.Titulo
        FROM Emprestimos
        JOIN Usuarios ON Emprestimos.Usuario_id = Usuarios.ID_usuario
        JOIN Livros ON Emprestimos.Livro_id = Livros.ID_livro
        WHERE Emprestimos.ID_emprestimo = %s
    """, [id])[0]

    return render(request, 'emprestimo_detalhes.html', {'emprestimo': emprestimo})
