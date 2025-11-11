from django.shortcuts import render, redirect
from django.db import connection
from datetime import date
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
        WHERE ID_usuario = %s
        ORDER BY ID_emprestimo DESC 
    """,[usuario_id])
    return render(request, 'emprestimos.html', {'dados': dados})


@login_required
def emprestimos_add(request):
    usuario_id = request.session.get('usuario_logado') 
    if request.method == 'POST':
        livro = request.POST.get('livro')
        data_emp = request.POST.get('data_emp') or str(date.today())
        data_prev = request.POST.get('data_prev') or str(date.today())
        status = 'pendente'

        if not livro:
            messages.error(request, "Você deve selecionar um livro para o empréstimo.")
            return redirect('emprestimos_add')
        if not usuario_id:
            messages.error(request, "Usuário não autenticado.")
            return redirect('login')

        livro_info = query("SELECT Quantidade_disponivel, Titulo FROM Livros WHERE ID_livro = %s", [livro])
        if not livro_info:
            messages.error(request, "Livro não encontrado.")
            return redirect('emprestimos_add')

        qtd_disponivel = livro_info[0]['Quantidade_disponivel']
        titulo_livro = livro_info[0]['Titulo']

        if qtd_disponivel <= 0:
            messages.error(request, f"O livro '{titulo_livro}' não está disponível para empréstimo.")
            return redirect('emprestimos_add')

        execute("""
            INSERT INTO Emprestimos (Usuario_id, Livro_id, Data_emprestimo, Data_devolucao_prevista, Status_emprestimo)
            VALUES (%s, %s, %s, %s, %s)
        """, [usuario_id, livro, data_emp, data_prev, status])

        execute("""
            UPDATE Livros
            SET Quantidade_disponivel = Quantidade_disponivel - 1
            WHERE ID_livro = %s
        """, [livro])

        messages.success(request, f"Empréstimo do livro '{titulo_livro}' registrado com sucesso!")
        return redirect('emprestimos')

    livros = query("SELECT * FROM Livros")
    return render(request, 'emprestimo_add.html', {
        'livros': livros
    })


@login_required
def emprestimos_edit(request, id):
    if request.method == 'POST':
        usuario = request.POST.get('usuario')
        novo_livro = request.POST.get('livro')
        data_emp = request.POST.get('data_emp')
        data_prev = request.POST.get('data_prev')
        data_real = request.POST.get('data_real')
        novo_status = request.POST.get('status')

        emprestimo_atual = query("SELECT * FROM Emprestimos WHERE ID_emprestimo = %s", [id])[0]
        status_antigo = emprestimo_atual['Status_emprestimo']
        livro_antigo = emprestimo_atual['Livro_id']

        if not data_emp:
            data_emp = emprestimo_atual['Data_emprestimo']
        if not data_prev:
            data_prev = emprestimo_atual['Data_devolucao_prevista']
        if not data_real:
            data_real = emprestimo_atual['Data_devolucao_real']

        try:
            novo_livro_id = int(novo_livro)
        except (TypeError, ValueError):
            messages.error(request, "Livro inválido.")
            return redirect('emprestimos_edit', id=id)

        estoque = {}
        if livro_antigo == novo_livro_id:
            if status_antigo != 'devolvido' and novo_status == 'Devolvido':
                estoque[novo_livro_id] = estoque.get(novo_livro_id, 0) + 1
            elif status_antigo == 'Devolvido' and novo_status != 'devolvido':
                estoque[novo_livro_id] = estoque.get(novo_livro_id, 0) - 1
        else:
            if status_antigo != 'devolvido':
                estoque[livro_antigo] = estoque.get(livro_antigo, 0) + 1
            if novo_status != 'devolvido':
                estoque[novo_livro_id] = estoque.get(novo_livro_id, 0) - 1

        for livro_id, qnt_disp in estoque.items():
            if qnt_disp < 0:
                livro_if = query("SELECT Quantidade_disponivel, Titulo FROM Livros WHERE ID_livro = %s", [livro_id])
                if not livro_if:
                    messages.error(request, "Livro não encontrado (id {}).".format(livro_id))
                    return redirect('emprestimos_edit', id=id)
                qtd_disponivel = livro_if[0]['Quantidade_disponivel']
                titulo = livro_if[0]['Titulo']
                if qtd_disponivel + qnt_disp < 0:
                    messages.error(request,
                        f"Não há cópias suficientes do livro '{titulo}' (está em {qtd_disponivel}).")
                    return redirect('emprestimos_edit', id=id)

        execute("""
            UPDATE Emprestimos
            SET Usuario_id = %s,
                Livro_id = %s,
                Data_emprestimo = %s,
                Data_devolucao_prevista = %s,
                Data_devolucao_real = %s,
                Status_emprestimo = %s
            WHERE ID_emprestimo = %s
        """, [usuario, novo_livro_id, data_emp, data_prev, data_real, novo_status, id])

        for livro_id, qnt_disp in estoque.items():
            if qnt_disp == 0:
                continue
            execute("""
                UPDATE Livros
                SET Quantidade_disponivel = Quantidade_disponivel + %s
                WHERE ID_livro = %s
            """, [qnt_disp, livro_id])

        messages.success(request, "Empréstimo atualizado com sucesso!")
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
    try:
        execute("DELETE FROM Emprestimos WHERE ID_emprestimo = %s", [id])
    except (TypeError, ValueError, IntegrityError):
        messages.error(request, "não foi possivel realizar")
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
