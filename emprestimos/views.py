from django.shortcuts import render, redirect
from django.db import connection
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
def emprestimos(request):
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
    """)
    return render(request, 'emprestimos.html', {'dados': dados})


@login_required
def emprestimos_add(request):
    if request.method == 'POST':
        usuario = request.POST['usuario']
        livro = request.POST['livro']
        data_emp = request.POST.get('data_emp') or str(date.today())
        data_prev = request.POST.get('data_prev') or str(date.today())
        status = request.POST['status']

        execute("""
            INSERT INTO Emprestimos (Usuario_id, Livro_id, Data_emprestimo, Data_devolucao_prevista, Status_emprestimo)
            VALUES (%s, %s, %s, %s, %s)
        """, [usuario, livro, data_emp, data_prev, status])

        return redirect('emprestimos')

    usuarios = query("SELECT * FROM Usuarios")
    livros = query("SELECT * FROM Livros")
    return render(request, 'emprestimos.html', {'usuarios': usuarios, 'livros': livros})


@login_required
def emprestimos_edit(request, id):
    if request.method == 'POST':
        usuario = request.POST['usuario']
        livro = request.POST['livro']
        data_emp = request.POST.get('data_emp')
        data_prev = request.POST.get('data_prev')
        data_real = request.POST.get('data_real')
        status = request.POST['status']

        emprestimo_atual = query("SELECT * FROM Emprestimos WHERE ID_emprestimo = %s", [id])[0]

        if not data_emp:
            data_emp = emprestimo_atual['Data_emprestimo']
        if not data_prev:
            data_prev = emprestimo_atual['Data_devolucao_prevista']
        if not data_real:
            data_real = emprestimo_atual['Data_devolucao_real']

        execute("""
            UPDATE Emprestimos
            SET Usuario_id = %s,
                Livro_id = %s,
                Data_emprestimo = %s,
                Data_devolucao_prevista = %s,
                Data_devolucao_real = %s,
                Status_emprestimo = %s
            WHERE ID_emprestimo = %s
        """, [usuario, livro, data_emp, data_prev, data_real, status, id])

        return redirect('emprestimos')

    emprestimo = query("SELECT * FROM Emprestimos WHERE ID_emprestimo = %s", [id])[0]
    usuarios = query("SELECT * FROM Usuarios")
    livros = query("SELECT * FROM Livros")
    return render(request, 'emprestimos_edit.html', {
        'emprestimo': emprestimo,
        'usuarios': usuarios,
        'livros': livros
    })


@login_required
def emprestimos_delete(request, id):
    execute("DELETE FROM Emprestimos WHERE ID_emprestimo = %s", [id])
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
